from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator
from .models import Election, Candidate, Vote

User = get_user_model()

class UserRegistrationSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password2 = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
    role = serializers.ChoiceField(
        choices=[('candidate', 'Candidate'), ('elector', 'Elector')],
        write_only=True
    )

    class Meta:
        model = User
        fields = ('username', 'email', 'password', 'password2', 'role', 'wallet_address')
        extra_kwargs = {
            'username': {'required': True},
            'wallet_address': {'required': False}
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        role = validated_data.pop('role')
        validated_data.pop('password2')
        
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            wallet_address=validated_data.get('wallet_address')
        )
        
        if role == 'candidate':
            user.is_candidate = True
        elif role == 'elector':
            user.is_elector = True
        
        user.save()
        return user

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        trim_whitespace=False
    )

    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')

        if email and password:
            user = authenticate(request=self.context.get('request'),
                                username=email, password=password)
            if not user:
                msg = 'Unable to log in with provided credentials.'
                raise serializers.ValidationError(msg, code='authorization')
        else:
            msg = 'Must include "email" and "password".'
            raise serializers.ValidationError(msg, code='authorization')

        attrs['user'] = user
        return attrs

class ElectionSerializer(serializers.ModelSerializer):
    is_active = serializers.BooleanField(read_only=True)
    created_by = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Election
        fields = '__all__'
        read_only_fields = (
            'id', 'created_at', 'created_by', 
            'contract_address', 'election_id', 'ipfs_hash',
            'is_approved'
        )

    def validate(self, data):
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError("End time must be after start time")
        return data

class CandidateSerializer(serializers.ModelSerializer):
    user = serializers.StringRelatedField()
    election = serializers.StringRelatedField()

    class Meta:
        model = Candidate
        fields = '__all__'
        read_only_fields = ('votes_received', 'approved')

class VoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vote
        fields = '__all__'
        read_only_fields = ('voter', 'voted_at', 'verified')