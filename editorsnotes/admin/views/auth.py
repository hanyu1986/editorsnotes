from editorsnotes.main.models import User
from editorsnotes.api.serializers.people import UserSerializer

from .common import BootstrappedBackboneView

class UserHomeView(BootstrappedBackboneView):
    model = User
    serializer_class = UserSerializer
    def get_object(self):
        return self.request.user
