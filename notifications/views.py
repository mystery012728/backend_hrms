from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from .models import Notification
from .serializers import NotificationSerializer

@extend_schema(responses={200: NotificationSerializer(many=True)})
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')
    serializer = NotificationSerializer(notifications, many=True, context={'request': request})
    return Response(serializer.data)

@extend_schema(request=None, responses={200: NotificationSerializer})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    notification.is_read = True
    notification.save()
    serializer = NotificationSerializer(notification, context={'request': request})
    return Response(serializer.data)

@extend_schema(request=None, responses={200: None})
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def mark_all_notifications_read(request):
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    return Response({"message": "All notifications marked as read."})
