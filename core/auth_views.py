from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


def build_user_payload(user):
    """
    Build the user info payload returned to frontend.
    Includes role + company info from UserProfile.
    """
    profile = getattr(user, "profile", None)  # related_name='profile' in UserProfile
    company = getattr(profile, "company", None) if profile else None

    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": getattr(profile, "role", None),
        "company": None if not company else {
            "id": company.id,
            "name": company.name,
            "code": company.code,
        }
    }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Customize /auth/login response to include user info.
    """
    def validate(self, attrs):
        data = super().validate(attrs)  # gives refresh + access
        data["user"] = build_user_payload(self.user)
        return data


class LoginView(TokenObtainPairView):
    """
    POST /api/auth/login/
    body: { "username": "...", "password": "..." }
    return: { refresh, access, user: {...} }
    """
    serializer_class = CustomTokenObtainPairSerializer


class MeView(APIView):
    """
    GET /api/auth/me/
    Header: Authorization: Bearer <access_token>
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(build_user_payload(request.user))