from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema

from employees.models import Employee
from .serializers import ProfileSerializer, ProfileUpdateSerializer


@extend_schema(
    responses={200: ProfileSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile(request):
    """
    Get the authenticated user's profile details.
    """
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = ProfileSerializer(employee, context={'request': request})
    return Response(serializer.data)


@extend_schema(
    request=ProfileUpdateSerializer,
    responses={200: ProfileSerializer}
)
@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def update_profile(request):
    """
    Update the authenticated user's profile details.
    """
    try:
        employee = Employee.objects.get(user=request.user)
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found for this user"},
            status=status.HTTP_404_NOT_FOUND
        )

    profile_image = request.FILES.get('profile_image')
    if profile_image:
        from employees.utils import has_face, resize_uploaded_image
        profile_image = resize_uploaded_image(profile_image)
        if not has_face(profile_image):
            return Response(
                {"message": "Image should contain Person face"},
                status=status.HTTP_400_BAD_REQUEST
            )

    serializer = ProfileUpdateSerializer(employee, data=request.data, partial=True)
    if serializer.is_valid():
        employee_obj = serializer.save()
        if profile_image:
            employee_obj.profile_image = profile_image
            employee_obj.save()

        response_serializer = ProfileSerializer(employee_obj, context={'request': request})
        return Response(response_serializer.data)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
