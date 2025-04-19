from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from .serializers import RegisterSerializer, LoginSerializer,DriverRegisterSerializer,ResetPasswordSerializer, ProfileSerializer
from utils.response import data_response
from utils.email import send_dynamic_email
from .models import User,EmailGroupModel,CarPic
from .utils import generate_unique_username
from django.utils.crypto import get_random_string
from django.shortcuts import render,HttpResponse

class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            phone_number = serializer.validated_data["phone_number"]

            if User.objects.filter(email=email).exists():
                return Response(
                    data_response(400, "Bad Request", {"error": "Email already exists"}),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    data_response(400, "Bad Request", {"error": "Phone number already exists"}),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = serializer.save()
            user.username = generate_unique_username()
            user.user_type = "customer"
            user.generate_verification_token()
            user.save()

            try:
                email_template = EmailGroupModel.objects.get(type="verification")
                verification_link = f"{email_template.fe_url}/{user.verification_token}"

                context_data = {
                    "username": user.first_name,
                    "verification_link": verification_link,
                }

                # Pass template data explicitly to the send_dynamic_email function
                email_response = send_dynamic_email(
                    subject=email_template.subject,
                    from_email=email_template.from_email,
                    recipient_email=user.email,
                    body_template=email_template.body_template,
                    context_data=context_data,
                )

                if email_response["status"] == "error":
                    return Response(
                        data_response(500, "Error sending email", {"error": email_response["message"]}),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            except EmailGroupModel.DoesNotExist:
                return Response(
                    data_response(500, "Error", {"error": "Verification email template not found."}),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                data_response(
                    status.HTTP_201_CREATED,
                    "User Created Successfully. Verify your email.",
                    None,
                ),
                status=status.HTTP_201_CREATED,
            )
        error_list = []
        for field, errors in serializer.errors.items():
            for error in errors:
                if error == "This field is required.":
                    error_list.append(f"{field.replace('_', ' ').capitalize()} is required.")
                else:
                    error_list.append(error)

        return Response(
            data_response(
                400,
                "Bad Request",
                {"errors": error_list},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )

class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]

            token, _ = Token.objects.get_or_create(user=user)
            print(user.first_name)
            return Response(
                data_response(
                    status.HTTP_200_OK,
                    "Login Successful",
                    {
                        "token": token.key,
                        "profile":ProfileSerializer(user).data
                    }
                ),
                status=status.HTTP_200_OK,
            )

        error_list = []
        for field, errors in serializer.errors.items():
            for error in errors:
                if error == "This field is required.":
                    error_list.append(f"{field.replace('_', ' ').capitalize()} is required.")
                else:
                    error_list.append(error)

        return Response(
            data_response(
                400,
                "Bad Request",
                {"errors": error_list},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )


# class VerifyEmailAPIView(APIView):
#     permission_classes = [AllowAny]

#     def get(self, request, token):
#         try:
#             user = User.objects.get(verification_token=token)
#             user.is_verified = True
#             user.verification_token = None
#             user.save()

#             return Response(
#                 data_response(status.HTTP_200_OK, "Email Verified Successfully", None),
#                 status=status.HTTP_200_OK,
#             )
#         except User.DoesNotExist:
#             return Response(
#                 data_response(status.HTTP_400_BAD_REQUEST, "Invalid token", None),
#                 status=status.HTTP_400_BAD_REQUEST,
#             )

def verify_account(request,token):
    try:
        user = User.objects.get(verification_token=token)
        user.is_verified = True
        user.verification_token = None
        user.save()
        return render(request=request,template_name="index.html")
    except User.DoesNotExist:
        return render(request=request,template_name="invalid_link.html")

class ResendVerificationEmailAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        phone_number = request.data.get("phone_number")
        try:
            user = User.objects.get(phone_number=phone_number)
            if user.is_verified:
                return Response(
                    data_response(400, "Bad Request", {"error": "Email is already verified"}),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user.generate_verification_token()
            email_template = EmailGroupModel.objects.get(type="verification")
            verification_link = f"{email_template.fe_url}/{user.verification_token}"

            context_data = {
                "username": user.first_name,
                "verification_link": verification_link,
            }

            send_dynamic_email(
                subject=email_template.subject,
                from_email=email_template.from_email,
                recipient_email=user.email,
                body_template=email_template.body_template,
                context_data=context_data,
            )

            return Response(
                data_response(200, "Verification email sent successfully", None),
                status=status.HTTP_200_OK,
            )
        except User.DoesNotExist:
            return Response(
                data_response(404, "Not Found", {"error": "User not found"}),
                status=status.HTTP_404_NOT_FOUND,
            )
        except EmailGroupModel.DoesNotExist:
            return Response(
                data_response(500, "Error", {"error": "Verification email template not found"}),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            print(request.auth.key, request.user.device_id)
            token = Token.objects.get(key=request.auth.key)
            request.user.device_id = None
            request.user.save()
            token.delete()

            return Response(
                data_response(status.HTTP_200_OK, "Logout Successful", None),
                status=status.HTTP_200_OK,
            )
        except Token.DoesNotExist:
            return Response(
                data_response(
                    status.HTTP_400_BAD_REQUEST, "Invalid token", None
                ),
                status=status.HTTP_400_BAD_REQUEST,
            )

class ForgotPasswordAPIView(APIView):
    permission_classes = [AllowAny,]
    def post(self, request, *args, **kwargs):
        phone_number = request.data.get('phone_number')
        
        try:
            user = User.objects.get(phone_number=phone_number)
            
            user.forget_token = get_random_string(64)
            user.save()
                        
            email_template = EmailGroupModel.objects.get(type="forgot-password")
            reset_link = f"{email_template.fe_url}/reset-password/{user.forget_token}"
            context_data = {
                "username": user.first_name,
                "reset_link": reset_link,
            }
            
            email_response = send_dynamic_email(
                subject=email_template.subject,
                from_email=email_template.from_email,
                recipient_email=user.email,
                body_template=email_template.body_template,
                context_data=context_data,
            )

            if email_response["status"] == "error":
                return Response(
                    {"error": email_response["message"]},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                {"message": "Password reset link sent successfully."},
                status=status.HTTP_200_OK,
            )

        except User.DoesNotExist:
            return Response(
                {"error": "User not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except EmailGroupModel.DoesNotExist:
            return Response(
                {"error": "Email template not found."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
            
class ResetPasswordAPIView(APIView):
    permission_classes = [AllowAny,]
    def post(self, request, token, *args, **kwargs):
        try:
            user = User.objects.get(forget_token=token)

            serializer = ResetPasswordSerializer(data=request.data)
            if serializer.is_valid():
                user.set_password(serializer.validated_data['new_password'])
                user.forget_token = None
                user.save()

                return Response(
                    {"message": "Password reset successful."},
                    status=status.HTTP_200_OK,
                )

            return Response(
                serializer.errors,
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        except User.DoesNotExist:
            return Response(
                {"error": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )


class DriverRegisterAPIView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        car_pics = request.data.getlist('car_pics',[])
        # if len(car_pics) == 0:
        #     return Response(
        #         data_response(400, "Bad Request", {"error": "Upload alteast one image"}),
        #         status=status.HTTP_400_BAD_REQUEST,
        #     )
            
        serializer = DriverRegisterSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data["email"]
            phone_number = serializer.validated_data["phone_number"]
            if User.objects.filter(email=email).exists():
                return Response(
                    data_response(400, "Bad Request", {"error": "Email already exists"}),
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    data_response(400, "Bad Request", {"error": "Phone number already exists"}),
                    status=status.HTTP_400_BAD_REQUEST,
                )

            driver = serializer.save()
            driver.generate_verification_token()
            driver.save()
            for car_pic in car_pics:
                CarPic.objects.create(user = driver,image = car_pic)               

            try:
                email_template = EmailGroupModel.objects.get(type="verification-driver")
                verification_link = f"{email_template.fe_url}/admin/authapi/user/{driver.id}/change/"

                context_data = {
                    "username": driver.first_name,
                    "verification_link": verification_link,
                }

                email_response = send_dynamic_email(
                    subject=email_template.subject,
                    from_email=email_template.from_email,
                    recipient_email=email_template.from_email,
                    body_template=email_template.body_template,
                    context_data=context_data,
                )

                if email_response["status"] == "error":
                    return Response(
                        data_response(500, "Error sending email", {"error": email_response["message"]}),
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )

            except EmailGroupModel.DoesNotExist:
                return Response(
                    data_response(500, "Error", {"error": "Verification email template not found."}),
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            return Response(
                data_response(
                    status.HTTP_201_CREATED,
                    "Driver Registered Successfully. Admin will verify your profile.",
                    None,
                ),
                status=status.HTTP_201_CREATED,
            )
            
        error_list = []
        for field, errors in serializer.errors.items():
            for error in errors:
                if error == "This field is required.":
                    error_list.append(f"{field.replace('_', ' ').capitalize()} is required.")
                else:
                    error_list.append(error)

        return Response(
            data_response(
                400,
                "Bad Request",
                {"errors": error_list},
            ),
            status=status.HTTP_400_BAD_REQUEST,
        )