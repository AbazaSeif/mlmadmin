from django.contrib.auth import login
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import get_object_or_404
from mlmadmin.models import MLM


def check_permission(function=None, login_url=None):
    def tmp(request, *args, **kwargs):
        if kwargs.get('object_id'):
            m = get_object_or_404(MLM, pk=kwargs.get('object_id'))
            if m.moderators.filter(username=request.user.username).exists():
                return function(request, *args, **kwargs)
            else:
                return HttpResponseNotFound()
        else:
            return function(request, *args, **kwargs)
    return tmp
    if function:
        return tmp(function)


def check_dump_permission(function=None, login_url=None):
    """this decorator is used only for Dump function"""
    def tmp(request, *args, **kwargs):
        if kwargs.get('object_id'):
            m = get_object_or_404(MLM, pk=kwargs.get('object_id'))
            if m.moderators.filter(
                    username=request.user.username,
                    is_staff=1).exists():
                return function(request, *args, **kwargs)
            else:
                return HttpResponseNotFound()
        else:
            return function(request, *args, **kwargs)
    return tmp
    if function:
        return tmp(function)
