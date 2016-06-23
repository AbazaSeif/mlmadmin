import ldap
import logging
from django.conf import settings
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from mlmadmin.models import MLM, alphanumeric_dash_underscore


ldap.set_option(ldap.OPT_REFERRALS, 0)

logging.basicConfig(
    format='%(asctime)s # %(levelname)-8s %(message)s',
    datefmt='%d/%m/%Y %H:%M:%S',
    filename=getattr(
        settings,
        'LOG_FILE_SYNC',
        '/var/log/mlmadmin_sync.log'),
    level=logging.INFO)


class LDAPsync():
    """
    Syncs LDAP groups and users
    """
    ldap_con = None
    allowed_groups_users = {}
    ldap_groups = {}

    def __init__(self):
        self.__ldap_connect()
        self.__get_groups()
        self.__get_users()
        self.__sync()
        self.__ldap_disconnect()

    def __ldap_connect(self):
        ldap_servers = settings.AUTH_LDAP_SERVER_URI_SET
        for ldap_server in ldap_servers:
            try:
                self.ldap_con = ldap.initialize('ldap://' + ldap_server)
                self.ldap_con.simple_bind_s(
                    settings.AUTH_LDAP_BIND_DN,
                    settings.AUTH_LDAP_BIND_PASSWORD)
                break
            except ldap.LDAPError as e:
                if ldap_server == ldap_servers[len(ldap_servers) - 1]:
                    logging.error(e)
                    raise e  # no connection to any of LDAP servers
                else:
                    continue

    def __ldap_disconnect(self):
        self.ldap_con.unbind()

    def __get_groups(self):
        """
        Gets LDAP groups in settings.AUTH_LDAP_GROUP_SEARCH
        """
        search_filter = '(objectClass=group)'
        try:
            raw_result = self.ldap_con.search_s(
                settings.AUTH_LDAP_GROUP_SEARCH, ldap.SCOPE_SUBTREE, search_filter)
        except ldap.NO_SUCH_OBJECT as e:
            raise

        for group in raw_result:
            group_cn = group[1]['cn'][0].lower()
            try:
                alphanumeric_dash_underscore(group_cn)
            except:
                logging.warn(
                    'group %s is not valid for the name of a mailing list' %
                    group_cn)
                continue
            self.ldap_groups[group_cn] = group[1]['member']

    def __get_users(self):

        for group, users in self.ldap_groups.items():
            users_list = []
            for user_DN in users:
                ldap_user = self.__get_user_by_DN(user_DN)
                if ldap_user:
                    users_list.append(ldap_user)
            self.allowed_groups_users[group] = users_list

    def __get_user_by_DN(self, user_DN):
        """
        Gets attributes 'sAMAccountName', 'mail', 'givenName', 'sn',
        for the user from LDAP, only if the user is enabled
        """
        search_filter = '(&(objectCategory=person)(objectClass=User)(!(userAccountControl:1.2.840.113556.1.4.803:=2)))'
        attributes = ('sAMAccountName', 'mail', 'givenName', 'sn', )

        raw_result = self.ldap_con.search_s(
            user_DN, ldap.SCOPE_BASE, search_filter, attributes)
        result_data = [
            entry for dn,
            entry in raw_result if isinstance(
                entry,
                dict)]

        if len(result_data) == 0:  # not found in LDAP
            return

        user_data = result_data[0]
        sAMAccountName = user_data['sAMAccountName'][0].lower()
        mail = user_data['mail'][0]

        if not mail:
            logging.warn('user %s has no email' % sAMAccountName)
            return
        try:
            validate_email(mail)
        except:
            logging.warn('user %s should have a valid email' % sAMAccountName)
            return

        givenName = user_data['givenName'][0]
        sn = user_data['sn'][0]
        return {
            'sAMAccountName': sAMAccountName,
            'mail': mail,
            'givenName': givenName,
            'sn': sn}

    def __get_or_create_user(self, item):
        user, created = User.objects.get_or_create(
            username=item['sAMAccountName'])
        if (user.first_name, user.last_name, user.email) != (
                item['givenName'], item['sn'], item['mail']):
            user.first_name = item['givenName']
            user.last_name = item['sn']
            user.email = item['mail']
            if created:
                logging.info('created user %s' % user.username)
                user.set_password(self.__generate_random_password())
            user.save()
            if not created:
                logging.info('changed user data for %s' % user.username)
        return user

    def __generate_random_password(self):
        import random
        return ''.join([random.SystemRandom().choice(
            'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(20)])

    def __sync(self):
        """
        Disables mailing lists which are not present in LDAP, removes users from moderators,
        if they are not in the LDAP group, add LDAP users
        """
        mlm_superusers = getattr(settings, 'MLM_SUPERUSERS', ['root'])
        try:
            flag_groups = getattr(settings, 'AUTH_LDAP_USER_FLAGS_BY_GROUP')
        except AttributeError as e:
            logging.error(e)
            raise

        for mlm in MLM.objects.all():
            if mlm.name not in self.allowed_groups_users:
                if mlm.enabled:
                    mlm.enabled = False
                    logging.info(
                        'disabled %s as it is not found in LDAP' %
                        mlm.name)
                    mlm.save()
            elif not mlm.enabled:
                mlm.enabled = True
                mlm.save()

        for group, users in self.allowed_groups_users.items():

            if group in [name for name, CN in flag_groups.values()]:
                flag = ''.join(
                    [k for k, v in flag_groups.items() if v[0] == group])
                # set the flag for the users in the flag group
                for item in users:
                    user = self.__get_or_create_user(item)
                    if hasattr(user, flag) and not getattr(user, flag):
                        setattr(user, flag, 1)
                        user.save()
                        logging.info(
                            'enabled flag %s for user %s' %
                            (flag, user.username))
                # check that mlm users not in the flag group have the flag
                # disabled
                for mlm_user in User.objects.all():
                    if mlm_user.username not in [
                            u['sAMAccountName'] for u in users]:
                        if hasattr(mlm_user, flag) and getattr(mlm_user, flag):
                            if mlm_user.username not in mlm_superusers:
                                setattr(mlm_user, flag, 0)
                                mlm_user.save()
                                logging.info(
                                    'disabled flag %s for user %s' %
                                    (flag, mlm_user.username))

            else:
                mlm, created = MLM.objects.get_or_create(name=group)

                if created:
                    logging.info('created mailing list %s' % mlm.name)
                else:
                    moderators = mlm.moderators.all()
                    for item in moderators:
                        if item.username not in [
                                k['sAMAccountName'] for k in users]:
                            if item.username not in mlm_superusers:
                                mlm.moderators.remove(item)
                                logging.info(
                                    'removed %s from mailing list %s' %
                                    (item.username, mlm.name))

                for item in users:
                    user = self.__get_or_create_user(item)

                    if not mlm.moderators.filter(
                            username=user.username).exists():
                        mlm.moderators.add(user)
                        logging.info(
                            'added user %s to moderators of %s' %
                            (user.username, mlm.name))


class Command(BaseCommand):
    help = 'Command to sync users and mailing lists with LDAP groups'

    def handle(self, *args, **options):
        ldapsync = LDAPsync()
