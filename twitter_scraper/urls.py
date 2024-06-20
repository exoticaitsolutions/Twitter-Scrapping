from django.urls import path
from . import views

urlpatterns = [
    path(
        "v1/twitter/tweets/profile/",
        views.get_tweeted_via_profile_name,
        name="get_Tweeted_via_profile_name",
    ),
    path(
        "v1/twitter/tweets/hashtag/",
        views.fetch_tweets_by_hash_tag,
        name="fetch_tweets_by_hash_tag",
    ),
    path(
        "v1/twitter/tweets/trending/",
        views.get_trending_tweets,
        name="get_trending_tweets",
    ),
    path(
        "v1/twitter/tweets/post/",
        views.get_tweets_by_id,
        name="get_tweets_by_id",
    ),
    path(
        "v1/twitter/tweets/comments/",
        views.get_comments_for_tweets,
        name="get_comments_for_tweets",
    ),
    path("create_instance/", views.create_instance, name="create_instance"),
    path("get_instance/", views.get_instance, name="get_instance"),
    path("release_instance/", views.release_instance, name="release_instance"),
    path("close_instance/", views.close_instance, name="close_instance"),
]