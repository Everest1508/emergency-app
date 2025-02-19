from rest_framework import serializers
from .models import User
from .utils import generate_unique_username
from django.contrib.auth import authenticate


class RegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ["first_name", "last_name", "phone_number", "email", "password", "confirm_password"]
        extra_kwargs = {"password": {"write_only": True}}

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return data

    def create(self, validated_data):
        password = validated_data.pop("password")
        validated_data.pop("confirm_password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        phone_number = data["phone_number"]

        try:
            user = User.objects.get(phone_number=phone_number)
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid phone number or password")

        user = authenticate(username=user.username, password=data["password"])
        if not user:
            raise serializers.ValidationError("Invalid phone number or password")

        if not user.is_verified:
            raise serializers.ValidationError("Email not verified")

        return {
            "user": user,
            "phone_number": phone_number,
        }


class DriverRegisterSerializer(serializers.ModelSerializer):
    confirm_password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = [
            'first_name', 'last_name', 'email', 'phone_number', "type",
            'license_pic', 'driver_pic', 'password',"confirm_password"
        ]
    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Passwords do not match."})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        password = validated_data.pop('password')
        user = User(**validated_data)
        user.set_password(password)
        user.user_type = 'driver'
        user.username = generate_unique_username()
        user.save()
        return user


class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True)
    confirm_password = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["confirm_password"]:
            raise serializers.ValidationError("Passwords do not match")
        return data


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["username", "first_name", "last_name","email","phone_number","user_type","license_pic","driver_pic","type"]
