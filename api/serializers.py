from django.contrib.auth.models import User
from rest_framework import serializers
from mlmadmin.models import MLM, Recipient


# Serializers define the API representation.
class UserSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = User
        fields = ('url', 'username', 'email', 'is_staff', 'is_superuser')


class MlmSerializer(serializers.Serializer):

    mlm = serializers.SerializerMethodField()
    moderators = serializers.StringRelatedField(many=True)
    enabled = serializers.BooleanField()
    address = serializers.SerializerMethodField()

    validated_data = None

    def get_address(self, obj):
        return ','.join([r.address for r in Recipient.objects.filter(
            mlm=obj.name).order_by('address')])

    def get_mlm(self, obj):
        return obj.name

    def is_valid(self):

        def has_fields(data):
            if isinstance(data, dict):
                if len([k for k in ['mlm', 'address'] if k in data]) == 2:
                    if isinstance(data['address'], list):
                        return True
            return

        if isinstance(self.initial_data, list):
            for item in self.initial_data:
                if not has_fields(item):
                    return
        else:
            if has_fields(self.initial_data):
                # make a list for the validated dict for the create method of
                # Class MlmViewSet
                self.validated_data = [self.initial_data]
                return True
            return

        self.validated_data = self.initial_data
        return True
