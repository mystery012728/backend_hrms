from django.utils import timezone

from rest_framework.decorators import (
    api_view,
    permission_classes,
    parser_classes
)

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from rest_framework.parsers import (
    MultiPartParser,
    FormParser
)



from employees.models import Employee

from .models import Attendance
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .serializers import AttendanceSerializer, CheckInRequestSerializer, CheckOutRequestSerializer
from django.conf import settings

# Preload DeepFace and warm up the ArcFace model at startup (module load time)
# to shift the heavy initialization cost out of the request-response lifecycle.
DeepFace = None
if getattr(settings, 'ENABLE_FACE_VERIFICATION', False):
    try:
        from deepface import DeepFace
        DeepFace.build_model("ArcFace")
    except Exception as e:
        import logging
        logging.getLogger(__name__).warning(f"Could not preload DeepFace/ArcFace: {e}")


@extend_schema(
    responses={200: AttendanceSerializer(many=True)},
    parameters=[
        OpenApiParameter(name='start_date', description='Filter by start date (YYYY-MM-DD)', required=False, type=str),
        OpenApiParameter(name='end_date', description='Filter by end date (YYYY-MM-DD)', required=False, type=str),
    ]
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def attendance_list(request):

    try:
        employee = Employee.objects.get(
            user=request.user
        )
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    start_date = request.query_params.get('start_date')
    end_date = request.query_params.get('end_date')

    filters = {'employee': employee}
    if start_date:
        filters['date__gte'] = start_date
    if end_date:
        filters['date__lte'] = end_date

    attendances = Attendance.objects.filter(**filters).order_by('-date')

    serializer = AttendanceSerializer(
        attendances,
        many=True,
        context={'request': request}
    )

    return Response(serializer.data)


@extend_schema(
    responses={200: AttendanceSerializer}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def todays_attendance(request):

    try:
        employee = Employee.objects.get(
            user=request.user
        )
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    today = timezone.now().date()

    attendance = Attendance.objects.filter(
        employee=employee,
        date=today
    ).first()

    if attendance is None:
        return Response(
            {
                "message": "No attendance marked for today"
            },
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = AttendanceSerializer(
        attendance,
        context={'request': request}
    )

    return Response(serializer.data)


@extend_schema(
    request=CheckInRequestSerializer,
    responses={201: AttendanceSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def check_in(request):

    try:
        employee = Employee.objects.get(
            user=request.user
        )
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    today = timezone.now().date()

    already_checked_in = Attendance.objects.filter(
        employee=employee,
        date=today
    ).exists()

    if already_checked_in:

        return Response(
            {
                "message": "Already checked in today"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    selfie = request.FILES.get('selfie')

    if not selfie:

        return Response(
            {
                "message": "Selfie is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    from employees.utils import has_face, resize_uploaded_image
    selfie = resize_uploaded_image(selfie)
    
    if not has_face(selfie):

        return Response(
            {
                "message": "Image should contain Person face"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not employee.profile_image:

        return Response(
            {
                "message": "Employee profile image not found"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    attendance = Attendance.objects.create(
        employee=employee,
        check_in=timezone.now(),
        selfie=selfie
    )

    if settings.ENABLE_FACE_VERIFICATION:
        try:
            if DeepFace is None:
                raise ImportError("DeepFace is not imported or initialization failed")
            result = DeepFace.verify(
                img1_path=employee.profile_image.path,
                img2_path=attendance.selfie.path,
                model_name="ArcFace",
                enforce_detection=False
            )

            if not result["verified"]:

                attendance.delete()

                return Response(
                    {
                        "message": "Face does not match"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:

            attendance.delete()

            return Response(
                {
                    "message": "Face verification failed",
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    serializer = AttendanceSerializer(
        attendance,
        context={'request': request}
    )

    return Response(
        serializer.data,
        status=status.HTTP_201_CREATED
    )


@extend_schema(
    request=CheckOutRequestSerializer,
    responses={200: AttendanceSerializer}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def check_out(request):

    try:
        employee = Employee.objects.get(
            user=request.user
        )
    except Employee.DoesNotExist:
        return Response(
            {"message": "Employee profile not found"},
            status=status.HTTP_404_NOT_FOUND
        )

    today = timezone.now().date()

    attendance = Attendance.objects.filter(
        employee=employee,
        date=today
    ).first()

    if attendance is None:

        return Response(
            {
                "message": "Please check in first"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    checkout_selfie = request.FILES.get('checkout_selfie')

    if not checkout_selfie:

        return Response(
            {
                "message": "Checkout selfie is required"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    from employees.utils import has_face, resize_uploaded_image
    checkout_selfie = resize_uploaded_image(checkout_selfie)
    
    if not has_face(checkout_selfie):

        return Response(
            {
                "message": "Image should contain Person face"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    if not employee.profile_image:

        return Response(
            {
                "message": "Employee profile image not found"
            },
            status=status.HTTP_400_BAD_REQUEST
        )

    attendance.check_out = timezone.now()
    attendance.checkout_selfie = checkout_selfie
    attendance.save()

    if settings.ENABLE_FACE_VERIFICATION:
        try:
            if DeepFace is None:
                raise ImportError("DeepFace is not imported or initialization failed")
            result = DeepFace.verify(
                img1_path=employee.profile_image.path,
                img2_path=attendance.checkout_selfie.path,
                model_name="ArcFace",
                enforce_detection=False
            )

            if not result["verified"]:

                # Revert check-out changes
                attendance.check_out = None
                if attendance.checkout_selfie:
                    attendance.checkout_selfie.delete(save=False)
                attendance.checkout_selfie = None
                attendance.save()

                return Response(
                    {
                        "message": "Face does not match"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        except Exception as e:

            # Revert check-out changes
            attendance.check_out = None
            if attendance.checkout_selfie:
                attendance.checkout_selfie.delete(save=False)
            attendance.checkout_selfie = None
            attendance.save()

            return Response(
                {
                    "message": "Face verification failed",
                    "error": str(e)
                },
                status=status.HTTP_400_BAD_REQUEST
            )

    serializer = AttendanceSerializer(
        attendance,
        context={'request': request}
    )

    return Response(serializer.data)