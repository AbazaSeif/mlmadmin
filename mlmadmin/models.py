import glob
import os
from collections import defaultdict
from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import User
from django.core.validators import RegexValidator
from django.db import models
from django.db.models.signals import pre_delete, post_delete, post_save, m2m_changed
from django.dispatch.dispatcher import receiver
from django.forms.models import ModelForm
from rest_framework.authtoken.models import Token

alphanumeric_dash_underscore = RegexValidator(
    r'^[0-9a-zA-Z_-]*$',
    'Only alphanumeric characters, dash and underscore are allowed.')


class MLM(models.Model):
    name = models.CharField(
        max_length=32,
        primary_key=True,
        validators=[alphanumeric_dash_underscore])
    moderators = models.ManyToManyField(User)
    enabled = models.BooleanField(default=True)
    synchronized = models.BooleanField(default=True)

    __original_name = None

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.__original_name = self.name

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        """
        if the name of the mlm instance is changed,
        assign the recipients to the new mlm
        """
        if self.name != self.__original_name:
            for recipient in Recipient.objects.filter(
                    mlm=self.__original_name):
                recipient.mlm = self
                recipient.save()
            try:
                self.__class__.objects.get(name=self.__original_name).delete()
            except Exception:
                pass

        super(self.__class__, self).save(force_insert, force_update, *args, **kwargs)

        mlmmj = MLMMJ(self)
        mlmmj.test_create()
        mlmmj.create_update_recipients()
        sync_alias_file()

        self.__original_name = self.name

    def __unicode__(self):
        return self.name


class MLMAdminForm(ModelForm):

    class Meta:
        model = MLM
        exclude = ('synchronized')


class Recipient(models.Model):
    address = models.EmailField()
    mlm = models.ForeignKey(MLM)

    __original_mlm = None

    class Meta:
        unique_together = (('address', 'mlm'),)

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        try:
            self.__original_mlm = self.mlm
        except Exception:  # a new recipient
            pass

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        """
        if the name of the mlm is changed,
        assign the recipients to the new mlm
        """
        super(self.__class__, self).save(force_insert, force_update, *args, **kwargs)

        mlmmj = MLMMJ(self.mlm)
        mlmmj.create_update_recipients()

        if self.__original_mlm:
            if self.mlm != self.__original_mlm:
                mlmmj = MLMMJ(self.__original_mlm)
                mlmmj.create_update_recipients()

        self.__original_mlm = self.mlm

    def __unicode__(self):
        return self.address


class RecipientAdmin(admin.ModelAdmin):
    model = Recipient
    list_display = ('address', 'mlm')
    search_fields = ('address', 'mlm__name')
    actions = ('delete_selected')

    def get_actions(self, request):
        actions = super(self.__class__, self).get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        obj.delete()
        mlmmj = MLMMJ(obj.mlm)
        mlmmj.create_update_recipients()


class MLMAdmin(admin.ModelAdmin):
    list_display = ('name', 'get_moderators', 'enabled', 'synchronized')
    search_fields = ('name', 'moderators__username', 'moderators__email')
    filter_horizonal = ('users')
    form = MLMAdminForm
    actions = ('sync_mlm', 'mark_unsynchronized')

    def get_moderators(self, obj):
        return ', '.join([m.username for m in obj.moderators.all()])
    get_moderators.short_description = "Moderators"

    def mark_unsynchronized(self, request, queryset):
        queryset.update(synchronized=False)
    mark_unsynchronized.short_description = 'Mark as unsynchronized'

    def sync_mlm(self, request, queryset):
        """
        Synchronize selected mlms from database to mlmmj files
        """
        errors = {}
        for qs in queryset:
            error = False
            mlm = MLM.objects.get(name=qs.name)

            # test if the mlmmj directories and files exist,
            # create if necessary
            mlmmj = MLMMJ(mlm)
            mlmmj.test_create()

            # dump moderators of the mlm to the mlmmj moderators file
            if not mlmmj.create_update_moderators():
                error = True
                errors['moderators'] = errors.get(
                    'moderators', []) + [mlm.name]

            # dump recipients of the mlm to the mlmmj subsribers.d directory
            if not mlmmj.create_update_recipients():
                error = True
                errors['recipients'] = errors.get(
                    'recipients', []) + [mlm.name]

            if error:
                mlm.synchronized = False
            else:
                mlm.synchronized = True
            mlm.save()

        # update the postfix file aliases
        sync_alias_file()

        if errors:
            from django.contrib import messages
            error_msg = 'failed! errors in synchronization:'
            for k, v in errors.items():
                error_msg += ' %s:%s' % (k, ','.join([i for i in v]))
            return messages.error(request, error_msg)

        return self.message_user(
            request, "selected mlms are successfully synchronized.")
    sync_mlm.short_description = "Synchronize selected mlms from database to mlmmj files"


class MLMMJ():
    """
    creates, updates, deletes mlmmj files
    """
    name = None  # string name of MLM
    mlm = None  # MLM instance
    path = None

    def __init__(self, mlm=None):

        self.path = getattr(settings, 'MLMMJ_SPOOL_DIR', '/var/spool/mlmmj')
        if self.path in ['', '/']:
            raise AttributeError(
                'root directory cannot be used for MLMMJ_SPOOL_DIR')
        if mlm:
            self.mlm = mlm
            self.name = mlm.name

    def test_create(self, name=None):
        if not name:
            name = self.name

        for s in [
                'PROJECT_ROOT',
                'COMPANY_MAIL_DOMAIN',
                'MLMMJ_ADMIN_EMAIL',
                'MLMMJ_TEXTPATHDEF',
                'MLMMJ_SPOOL_CHOWN_USER']:
            getattr(settings, s)

        os.system(
            '%s/mlmmj-make-ml -D %s -o %s -t %s -c %s -L %s' %
            (settings.PROJECT_ROOT,
             settings.COMPANY_MAIL_DOMAIN,
             settings.MLMMJ_ADMIN_EMAIL,
             settings.MLMMJ_TEXTPATHDEF,
             settings.MLMMJ_SPOOL_CHOWN_USER,
             name))

    def create_update_moderators(self, del_moderator=None):
        """
        Updates the mlmj file 'moderators'
        """
        if del_moderator:
            # exclude the given del_moderator from the query
            moderators = '\n'.join([m for m in self.mlm.moderators.exclude(
                username=del_moderator).values_list('email', flat=True).distinct().order_by('email')])
        else:
            moderators = '\n'.join([m for m in self.mlm.moderators.all().values_list(
                'email', flat=True).distinct().order_by('email')])
        try:
            fd = open(
                os.path.join(
                    self.path,
                    self.name,
                    'control/moderators'),
                'w')
            fd.write(moderators)
            fd.close()
        except Exception:
            return
        return True

    def create_update_recipients(self):
        subscribers_dir = os.path.join(self.path, self.name, 'subscribers.d')

        try:
            files_to_remove = glob.glob(subscribers_dir + '/*')
            for item in files_to_remove:
                os.remove(item)

            recipients_list = Recipient.objects.filter(
                mlm=self.name).values_list(
                'address', flat=True).order_by('address')
            d = defaultdict(list)

            for items in recipients_list:
                d[items[0]].append(items)

            for fname, emails in d.items():
                fd = open(os.path.join(subscribers_dir, fname), 'w+')
                fd.write('\n'.join([item for item in emails]))
                fd.close()
        except IOError:
            return
        return True

    def cleanup_bounces(self):
        bounce_dir = os.path.join(self.path, self.name, 'bounce')
        if os.path.exists(bounce_dir):
            files_to_remove = glob.glob(bounce_dir + '/*')
            for item in files_to_remove:
                os.remove(item)

    def delete_mlmmj_dir(self):
        mlmmj_dir = os.path.join(self.path, self.name)
        if os.path.exists(mlmmj_dir):
            import shutil
            shutil.rmtree(mlmmj_dir)


def sync_alias_file():
    """
    Synchronizes the content of the postfix file aliases
    """
    mlmmj_spool_dir = getattr(settings, 'MLMMJ_SPOOL_DIR', '/var/spool/mlmmj')
    if mlmmj_spool_dir in ['', '/']:
        raise AttributeError(
            'root directory cannot be used for MLMMJ_SPOOL_DIR')
    mlmmj_bin_dir = getattr(settings, 'MLMMJ_BIN_DIR', '/usr/bin')

    aliases = '\n'.join(
        [
            '%(name)s:  "|%(mlmmj_bin_dir)s/mlmmj-receive -L %(mlmmj_spool_dir)s/%(name)s/"' %
            {
                'name': x.name,
                'mlmmj_bin_dir': mlmmj_bin_dir,
                'mlmmj_spool_dir': mlmmj_spool_dir} for x in MLM.objects.all().order_by('name') if x.enabled])
    fd = open(os.path.join(mlmmj_spool_dir, 'mlmmj'), 'w+')
    fd.write(aliases)
    fd.close()
    os.system('/usr/sbin/postalias hash:%s/mlmmj' % mlmmj_spool_dir)


@receiver(m2m_changed, sender=MLM.moderators.through)
def _mlm_model_m2m_save(
        sender,
        instance,
        action,
        reverse,
        model,
        pk_set,
        **kwargs):
    if action == 'post_add':
        mlmmj = MLMMJ(instance)
        mlmmj.create_update_moderators()


@receiver(post_delete, sender=MLM)
def _mlm_model_delete(sender, instance, **kwargs):
    mlmmj = MLMMJ(instance)
    mlmmj.delete_mlmmj_dir()
    sync_alias_file()


@receiver(post_save, sender=User)
def _user_model_save(sender, instance, **kwargs):
    """
    Makes mlmmj files 'moderators' actual upon changing the User instance in the admin site
    """
    for mlm in MLM.objects.all():
        if mlm.moderators.filter(username=instance.username).exists():
            mlmmj = MLMMJ(mlm)
            mlmmj.create_update_moderators()


@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    """
    Create a token when a user is created
    """
    if hasattr(settings, 'REST_FRAMEWORK_TOKEN_USER_CREATE'):
        if settings.REST_FRAMEWORK_TOKEN_USER_CREATE:
            if created:
                Token.objects.create(user=instance)


@receiver(pre_delete, sender=User)
def _user_model_delete(sender, instance, **kwargs):
    """
    Makes mlmmj files 'moderators' actual before deleting the User instance in the admin site
    """
    for mlm in MLM.objects.all():
        if mlm.moderators.filter(username=instance.username).exists():
            mlmmj = MLMMJ(mlm)
            mlmmj.create_update_moderators(instance.username)


admin.site.register(MLM, MLMAdmin)
admin.site.register(Recipient, RecipientAdmin)
