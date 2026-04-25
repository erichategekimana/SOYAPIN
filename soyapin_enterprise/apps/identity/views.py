from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import User, UserAddress
from .serializers import UserSerializer, UserAddressSerializer
from rest_framework import permissions

class UserViewSet(viewsets.ModelViewSet):
    """
    Provides CRUD operations for users
    GET /users/ - list all
    POST /users/ - create
    GET /users/1/ - retrieve
    PUT /users/1/ - update
    DELETE /users/1/ - delete
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """GET /api/v1/identity/users/me/ - returns current user"""
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    



class AddressViewSet(viewsets.ModelViewSet):
    """
    Handles CRUD for shipping addresses.
    Filters queryset so users only see their own addresses.
    """
    queryset = UserAddress.objects.all()
    serializer_class = UserAddressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return UserAddress.objects.none()  # Return empty queryset for schema generation
        
        # Only return addresses belonging to the logged-in user
        return UserAddress.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        # Automatically set the user field to the current user when saving
        serializer.save(user=self.request.user)