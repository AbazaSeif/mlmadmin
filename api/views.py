from api.serializers import UserSerializer, MlmSerializer
from django.contrib.auth.models import User
from django.core.validators import validate_email
from mlmadmin.models import MLM, MLMMJ, Recipient
from rest_framework import status
from rest_framework import viewsets
from rest_framework.response import Response


# ViewSets define the view behavior.
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class MlmViewSet(viewsets.ViewSet):
    queryset = MLM.objects.all()
    serializer_class = MlmSerializer

    def list(self, request):
        serializer = MlmSerializer(self.queryset, many=True)
        return Response(serializer.data)

    def create(self, request):

        serializer = MlmSerializer(data=request.data)

        if serializer.is_valid():
            updated_mlm = []
            not_found_mlm = []

            for item in serializer.validated_data:

                try:
                    mlm = MLM.objects.get(name=item['mlm'])
                except:
                    not_found_mlm.append(item['mlm'])
                    continue

                # delete the existing subscribers from the mailing list
                Recipient.objects.filter(mlm=mlm.name).delete()

                for email in item['address']:
                    if email[0] == '/':  # mlmmj cannot create a file named '/' in Linux
                        continue
                    try:
                        validate_email(email)
                    except:
                        continue
                    recipient = Recipient()
                    recipient.mlm = mlm
                    recipient.address = email
                    try:
                        recipient.save()
                    except:
                        pass  # cannot save to database

                mlmmj = MLMMJ(mlm)
                mlmmj.create_update_recipients()

                updated_mlm.append(mlm.name)

            if not updated_mlm:
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_201_CREATED

            return Response({'Success': '%s' % ','.join(
                [m for m in updated_mlm]), 'Error': '%s' % ','.join([n for n in not_found_mlm])}, status_code)
        return Response({'Error': 'malformed JSON string'},
                        status=status.HTTP_400_BAD_REQUEST)
