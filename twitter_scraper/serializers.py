"""
Module containing serializers for Twitter profiles, hashtags, and tweet URLs.
"""

from rest_framework import serializers


class TwitterProfileSerializers(serializers.Serializer):
    """
    Serializer for Twitter profiles.
    """

    Profile_name = serializers.CharField(required=True)

    def create(self, validated_data):
        """
        Create method implementation.
        """
        pass

    def update(self, instance, validated_data):
        """
        Update method implementation.
        """
        pass


class TweetHashtagSerializer(serializers.Serializer):
    """
    Serializer for tweet hashtags.
    """

    hashtags = serializers.CharField(required=True)

    def create(self, validated_data):
        """
        Create method implementation.
        """
        pass

    def update(self, instance, validated_data):
        """
        Update method implementation.
        """
        pass


class TweetUrlSerializer(serializers.Serializer):
    """
    Serializer for tweet URLs.
    """

    user_name = serializers.CharField(required=True)
    post_ids = serializers.ListField(child=serializers.IntegerField(), required=True)

    @staticmethod
    def validate_post_id(value):
        """
        Validate post ID to ensure it's an integer.
        """
        try:
            # Try to convert the value to an integer
            post_id_int = int(value)
        except ValueError:
            # If conversion fails, raise a validation error
            raise serializers.ValidationError("Post ID must be an integer")

        # Return the integer value
        return post_id_int

    def create(self, validated_data):
        """
        Create method implementation.
        """
        pass

    def update(self, instance, validated_data):
        """
        Update method implementation.
        """
        pass
