from django.core.management.base import BaseCommand, CommandError
from mlmadmin.models import MLM, MLMMJ, sync_alias_file


class Command(BaseCommand):
    help = 'Command to sync mlmmj files'

    def handle(self, *args, **options):
        for mlm in MLM.objects.filter(enabled=1):
            mlmmj = MLMMJ(mlm)
            mlmmj.test_create()
            mlmmj.create_update_moderators()
            mlmmj.create_update_recipients()
        sync_alias_file()
