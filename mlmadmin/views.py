import csv
import email
import json
import os
import rfc822
from annoying.decorators import render_to
from dateutil import parser
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render, render_to_response
from django.template import RequestContext
from django.views.decorators.csrf import csrf_exempt
from email.header import decode_header
from itertools import groupby
from mlmadmin.decorators import check_permission, check_dump_permission
from mlmadmin.forms import *
from mlmadmin.models import *
from subprocess import Popen


class SList:

    MDIR = None
    BDIR = None

    def __init__(self, listname):

        mlmmj_spool_dir = getattr(
            settings,
            'MLMMJ_SPOOL_DIR',
            '/var/spool/mlmmj')
        if mlmmj_spool_dir in ['', '/']:
            raise AttributeError(
                'root directory cannot be used for MLMMJ_SPOOL_DIR')
        self.MDIR = os.path.join(mlmmj_spool_dir, listname, 'moderation')
        self.BDIR = os.path.join(mlmmj_spool_dir, listname, 'bounce')

    def getheader(self, header_text, default="ascii"):
        headers = decode_header(header_text)
        header_sections = [
            unicode(
                text,
                charset or default) for text,
            charset in headers]
        return u"".join(header_sections)

    def getBounceMessage(self, fname):
        filename = '%s%s' % (fname, '.lastmsg')
        leaves = []
        msgbody = ''
        attachments = []
        hasHTML = False
        msgplain = []
        if os.path.exists(os.path.join(self.BDIR, filename)):
            try:
                fd = open(os.path.join(self.BDIR, filename), 'r')
                msg = email.message_from_file(fd)
                fd.close()
            except IOError:
                return
            getAllParts(msg, leaves)
            for i in leaves:
                if i['content-type'] == 'text/plain':
                    msgbodyplain = i['msg'].get_payload(
                        decode=True).replace(
                        '\n',
                        '<br>')
                    if i['charset']:
                        msgbodyplain = msgbodyplain.decode(i['charset'])
                    msgplain.append(msgbodyplain)

            if not hasHTML:
                msgbody = '<br>'.join(msgplain)
            return json.dumps(
                {'body': msgbody, 'subject': fname.replace('=', '@')})
        else:
            return

    def getModerationMessage(self, filename):
        leaves = []
        if os.path.exists(os.path.join(self.MDIR, filename)):

            try:
                fd = open(os.path.join(self.MDIR, filename), 'r')
                msg = email.message_from_file(fd)
                fd.close()
            except IOError:
                return

            subject = self.getheader(msg.get('subject'))
            getAllParts(msg, leaves)
            cids = {}
            msgbody = ''
            attachments = []
            hasHTML = False
            for i in leaves:
                if i['content-type'] == 'text/html':
                    hasHTML = True
                    msgbody = re.findall(
                        ur'<body[^>]*?>(.*?)</body>',
                        i['msg'].get_payload(
                            decode=True),
                        re.DOTALL)[0].decode(
                        i['charset'])
                if i['content-type'] == 'text/plain':
                    msgbodyplain = i['msg'].get_payload(
                        decode=True).decode(
                        i['charset']).replace(
                        '\n',
                        '<br>')
                if 'image' in i['content-type']:
                    if i['content-id']:
                        cid = i['content-id'].split('<')[-1].split('>')[0]
                        filename = i['msg'].get_filename()
                        try:
                            fd = open(
                                os.path.join(
                                    settings.MEDIA_UPLOAD_ROOT,
                                    filename),
                                'wb')
                            fd.write(i['msg'].get_payload(decode=True))
                            fd.close()
                        except IOError:
                            continue
                        cids['cid:%s' % cid] = '%s%s' % (
                            settings.MEDIA_UPLOAD_URL, filename)
                if 'application' in i[
                        'content-type'] or ('text' not in i['content-type'] and i['content-id'] is None):
                    attachments.append(
                        {'filename': i['msg'].get_filename(), 'type': i['msg'].get_content_type()})

                for cid, path in cids.items():
                    msgbody = msgbody.replace(cid, path)
                if not hasHTML:
                    msgbody = msgbodyplain
            return json.dumps(
                {'body': msgbody, 'attachments': attachments, 'subject': subject})

    def blist(self):
        dlist = []
        i = 0
        if os.path.exists(self.BDIR):
            for fname in os.listdir(self.BDIR):
                if 'lastmsg' not in fname:
                    try:
                        fd = open(os.path.join(self.BDIR, fname), 'r')
                        dates = fd.readlines()
                        fd.close()
                    except IOError:
                        continue
                    lastdate = dates[-1].split('#')[1]
                    email = '@'.join(fname.split('='))
                    d = {
                        'id': i,
                        'email': email,
                        'fname': fname,
                        'date': parser.parse(lastdate),
                        'count': len(dates)}
                    i = i + 1
                    dlist.append(d)
        return sorted(dlist, key=lambda k: k['date'], reverse=True)

    def mlist(self):
        data = []
        if os.path.exists(self.MDIR):
            for fname in os.listdir(self.MDIR):
                if not fname.endswith('.sending'):
                    p = email.Parser.Parser()

                    try:
                        fd = open(os.path.join(self.MDIR, fname), 'r')
                        msg = p.parse(fd)
                        fd.close()
                    except IOError:
                        continue

                    h = self.getheader(msg['subject'])
                    dd = parser.parse(msg['date'])

                    d = {
                        'id': fname,
                        'subject': h,
                        'from': rfc822.parseaddr(
                            msg.get('From'))[1],
                        'to': msg['to'],
                        'date': dd}

                    data.append(d)

            return sorted(data, key=lambda k: k['date'], reverse=True)
        else:
            return []


def task_running(request, listname):
    """
    Checks if a task for the mailing list is in progress,
    if positive, sends a warning message and disables changes in subscribers
    """
    mlmmj_send = os.path.join(
        getattr(
            settings,
            'MLMMJ_BIN_DIR',
            '/usr/bin'),
        'mlmmj-send')
    listdir = os.path.join(
        getattr(
            settings,
            'MLMMJ_SPOOL_DIR',
            '/var/spool/mlmmj'),
        listname,
        '')
    proc_user = getattr(settings, 'MLMMJ_SPOOL_CHOWN_USER', 'nobody')
    try:
        ps_output = Popen(['ps', '-f', '-U', proc_user],
                          stdout=subprocess.PIPE).communicate()[0]
    except:
        return
    if mlmmj_send and listdir in ps_output:
        messages.add_message(
            request,
            messages.WARNING,
            'An active task is in progress, please wait.')
        return True


def getAllParts(msg, leaves):
    if msg.is_multipart():
        for part in msg.get_payload():
            getAllParts(part, leaves)
    else:
        leaves.append({'content-id': msg.get('content-id'),
                       'msg': msg,
                       'content-type': msg.get_content_type(),
                       'charset': msg.get_content_charset()})


def getParts(msg, leaves):
    if msg.is_multipart():
        for part in msg.get_payload():
            if 'text/plain' in part.get_content_type():
                getParts(part, leaves)
            elif 'message/rfc822' in part.get_content_type():
                getParts(part, leaves)
    else:
        leaves.append(msg)


def moderation_ajax(request, object_id):
    if request.POST:
        print request.POST.get('id')
        print request.POST.get('from')


def redirect(request):
    """
    redirect to local authentication
    web browser should have a redirect directive
    """
    logout(request)
    return HttpResponseRedirect('/redirect/')


def signout(request):
    logout(request)
    return HttpResponseRedirect('/mlmadmin/')


def bulk_search(request, object_id):
    mlm = get_object_or_404(MLM, pk=object_id)

    if request.POST:

        if task_running(request, object_id):
            return HttpResponseRedirect('/mlmadmin/' + object_id)

        post_values = request.POST.copy()
        msgs = []
        for k, i in post_values.items():
            if k.isdigit():
                if not i:
                    recipient = Recipient.objects.get(pk=k)
                    recipient.delete()
                    msgs.append(
                        'email address %s is deleted from %s' %
                        (recipient.address, object_id))
                try:
                    validate_email(i)
                    recipient = Recipient.objects.get(pk=k)
                    addr = recipient.address
                    recipient.address = i
                    if addr != i:
                        recipient.save()
                    if addr != i:
                        msgs.append(
                            'email address %s is changed to %s' %
                            (addr, i))
                except:
                    pass

        mlmmj = MLMMJ(mlm)
        mlmmj.create_update_recipients()

        for msg in msgs:
            messages.add_message(request, messages.INFO, msg)
        return HttpResponseRedirect('/mlmadmin/' + object_id)


def start_response(status, headers):
    status, reason = status.split(' ', 1)
    django_response.status_code = int(status)
    for header, value in headers:
        django_response[header] = value


def get_mtasks(object_id):
    """
    get moderation tasks
    """
    sl = SList(object_id)
    return len(sl.mlist())


@render_to('mlmadmin/main.html')
@login_required
@check_permission
def main(request, object_id=None):
    """
    user start page
    """
    mlm = MLM.objects.filter(moderators=request.user, enabled=1)
    if not object_id:
        try:
            object_id = request.session['current_mlm']
        except:
            try:
                object_id = mlm[0].name
            except:
                # user is not subscribed to any mailing lists
                messages.add_message(
                    request,
                    messages.ERROR,
                    'You are not assigned to any mailing list')
                return {}
        return HttpResponseRedirect('/mlmadmin/' + object_id)
    request.session['current_mlm'] = object_id

    return {
        'object_list': [],
        'groups': mlm,
        'current_mlm': object_id,
        'mtasks': get_mtasks(object_id),
        'is_staff': request.user.is_staff}


@render_to('mlmadmin/search.html')
@check_permission
def search(request, object_id):
    mlm = MLM.objects.filter(moderators=request.user, enabled=1)

    if request.POST:
        s = request.POST.get('s')
        recipients = Recipient.objects.filter(
            mlm=object_id).filter(
            address__contains=s).order_by('address')

        return {
            'r': recipients,
            'size': len(recipients),
            'current_mlm': object_id,
            'groups': mlm,
            'mtasks': get_mtasks(object_id),
            'is_staff': request.user.is_staff}
    else:
        return HttpResponseRedirect('/mlmadmin/' + object_id)


@render_to('mlmadmin/moderation.html')
@check_permission
def moderation(request, object_id):
    if not request.POST:
        mlm = MLM.objects.filter(moderators=request.user, enabled=1)
        sl = SList(object_id)

        return {
            'groups': mlm,
            'current_mlm': object_id,
            'mlist': sl.mlist(),
            'is_staff': request.user.is_staff}
    else:
        id = request.POST.get('id')
        mail_from = request.POST.get('from')
        action = request.POST.get('action')
        if action != 'getmessagebody':
            mail_to = '%s+%s-%s@%s' % (object_id,
                                       action, id, settings.COMPANY_MAIL_DOMAIN)

            try:
                send_mail('ok', 'ok', mail_from, [mail_to])
            except:
                pass
            return HttpResponse(json.dumps(['ok']))
        else:
            sl = SList(object_id)
            return HttpResponse(sl.getModerationMessage(id))


@login_required
@check_dump_permission
def dump(request, object_id):
    response = HttpResponse(mimetype='text/csv')
    response['Content-Disposition'] = 'attachment; filename=%s.csv' % object_id
    writer = csv.writer(response)

    data = sorted(
        Recipient.objects.filter(
            mlm=object_id).values_list(
            'address',
            flat=True))

    for i in data:
        writer.writerow([i])
    return response


@login_required
@check_permission
def add(request, object_id):
    mlm = MLM.objects.filter(moderators=request.user, enabled=1)

    if request.POST:

        if task_running(request, object_id):
            return HttpResponseRedirect('/mlmadmin/' + object_id)

        post_values = request.POST.copy()
        form = AddForm(request.POST)

        if form.is_valid():
            if 'delete_before_store' in request.POST:
                result = form.save(True)
            else:
                result = form.save()

            mlm_to_update = get_object_or_404(MLM, pk=object_id, enabled=1)
            mlmmj = MLMMJ(mlm_to_update)
            mlmmj.create_update_recipients()

            if result['success']:
                messages.add_message(
                    request,
                    messages.INFO,
                    'the email addresses are successfully added to the mailing list %s' %
                    object_id)
            for i in result['error']:
                messages.add_message(
                    request,
                    messages.ERROR,
                    'the email address %s already exists in the mailing list.' %
                    i)

            return HttpResponseRedirect('/mlmadmin/' + object_id)
        else:
            messages.add_message(
                request,
                messages.ERROR,
                'No valid email addresses are found')
            return render_to_response('mlmadmin/add.html',
                                      {'form': form,
                                       'groups': mlm,
                                       'current_mlm': object_id,
                                       'mtasks': get_mtasks(object_id),
                                          'is_staff': request.user.is_staff},
                                      context_instance=RequestContext(request))
    else:

        form = AddForm(initial={'mlm': object_id})

        return render_to_response('mlmadmin/add.html',
                                  {'form': form,
                                   'groups': mlm,
                                   'current_mlm': object_id,
                                   'mtasks': get_mtasks(object_id),
                                      'is_staff': request.user.is_staff},
                                  context_instance=RequestContext(request))


@login_required
def compose(request, object_id):
    mlm = MLM.objects.filter(moderators=request.user, enabled=1)

    if not request.POST:
        form = ComposeForm(initial={'sender': request.user.email})
        form.fields['sender'].widget.attrs['readonly'] = True
        form.fields['to'].choices = [(x.name, x.name) for x in mlm]
        return render(request,
                      'mlmadmin/compose.html',
                      {'form': form,
                       'groups': mlm,
                       'current_mlm': object_id,
                       'mtasks': get_mtasks(object_id),
                       'is_staff': request.user.is_staff})
    else:
        form = ComposeForm(request.POST, request.FILES)
        form.fields['to'].choices = [(x.name, x.name) for x in mlm]

        if form.is_valid():
            from_email = request.user.email
            data = form.cleaned_data
            subject = data.get('subject')

            for to in data.get('to'):
                to_email = "%s@%s" % (to, settings.COMPANY_MAIL_DOMAIN)
                text_content = strip_tags(data.get('body'))
                html_content = "<html><body>%s</body></html>" % data.get(
                    'body')
                msg = EmailMultiAlternatives(
                    subject,
                    text_content,
                    from_email,
                    [to_email])
                msg.attach_alternative(html_content, "text/html")

                if data.get('files') is not None:
                    for k, v in data.get('files').items():
                        for i in v:
                            msg.attach(i.name, i.read(), i.content_type)
                msg.send()

            messages.add_message(
                request,
                messages.INFO,
                'Your email is successfully sent to moderation')
            return HttpResponseRedirect('/mlmadmin/' + object_id)
        else:
            form.fields['to'].choices = [(x.name, x.name) for x in mlm]
            return render(request,
                          'mlmadmin/compose.html',
                          {'form': form,
                           'groups': mlm,
                           'current_mlm': object_id,
                           'mtasks': get_mtasks(object_id),
                           'is_staff': request.user.is_staff})


@check_permission
def bounce(request, object_id):

    if request.POST.get('cleanup'):
        mlmmj = MLMMJ(MLM.objects.get(pk=object_id))
        mlmmj.cleanup_bounces()
        return HttpResponse()

    sl = SList(object_id)
    if not request.POST:
        mlm = MLM.objects.filter(moderators=request.user, enabled=1)

        bounces = sl.blist()
        return render_to_response('mlmadmin/bounce.html',
                                  {'groups': mlm,
                                   'current_mlm': object_id,
                                   'bounces': bounces,
                                   'mtasks': get_mtasks(object_id),
                                      'is_staff': request.user.is_staff},
                                  context_instance=RequestContext(request))
    else:
        fname = request.POST.get('id')

        return HttpResponse(sl.getBounceMessage(fname))


@login_required
def help(request):
    return render_to_response(
        'mlmadmin/help.html',
        context_instance=RequestContext(request))


django_response = HttpResponse()
