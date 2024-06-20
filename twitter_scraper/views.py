import threading
from concurrent.futures import ThreadPoolExecutor
from time import sleep

# Cloudflare configuration....
import requests
from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from rest_framework import status
from rest_framework.decorators import api_view
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
)
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait

from .utils import (
    twitter_login_auth,
    message_json_response,
    save_data_in_directory,
    random_sleep,
    tweet_content_exists,
    set_cache,
    get_cache,
    save_data_and_return,
)
from .web_driver import InitializeDriver

CLOUDFLARE_WORKER_URL = "https://<your-cloudflare-worker-url>"
##################################################################

MAX_THREAD_COUNT = 5
MAX_EXCEPTION_RETRIES = 3
NUMBER_OF_POSTS = 2
CACHE_TIMEOUT = 60 * 15

driver_initializer = InitializeDriver()


def print_current_thread():
    current_thread = threading.current_thread()
    print("---------- Current Thread:", current_thread.name)


def retry_exception(recalling_method_name, any_generic_parameter, retry_count=0, exception_name=None):
    """
    Retry a method up to MAX_EXCEPTION_RETRIES times when an exception occurs,
    with a random delay between retries.

    Args:
    - recalling_method_name: The method to retry.
    - any_generic_parameter: Any parameter needed by the method.
    - retry_count: Current retry attempt count (default is 0).
    - exception_name: Name or type of the exception being handled (optional).

    Returns:
    - Tuple (False, "Element not found") if retry attempts are exhausted,
      indicating the method failed after retries.
    - Result of recalling_method_name if successful within retry attempts.

    """
    # Check if retry attempts are exhausted
    if retry_count < MAX_EXCEPTION_RETRIES:
        retry_count += 1
        # Retry the function after a delay
        print(f"Retrying '{exception_name}' in '{recalling_method_name}', Attempt #{retry_count}")
        random_sleep()  # Add a random delay before retrying
        return recalling_method_name(any_generic_parameter, retry_count)
    else:
        # Return an indication that retry attempts are exhausted
        print("All retry attempts exhausted. Throwing error now...")
        return False, "Element not found"


def scrape_profile_tweets(profile_name=None, retry_count=0, full_url=None):
    """
       Scrapes tweets from a Twitter profile.

       Args:
       - profile_name (str): The Twitter profile name to scrape tweets from.
       - retry_count (int, optional): Current retry attempt count. Default is 0.
       - full_url (str, optional): Full URL associated with the profile. Default is None.

       Returns:
       - Tuple (bool, list or str):
           - If successful, returns (True, scraped_data).
             scraped_data is a list of dictionaries containing scraped tweet information:
             {
                 "Name": Name of the profile being scraped,
                 "UserTag": Twitter handle of the user,
                 "Timestamp": Timestamp of the tweet,
                 "TweetContent": Text content of the tweet,
                 "Reply": Number of replies to the tweet,
                 "Retweet": Number of retweets of the tweet,
                 "Likes": Number of likes on the tweet
             }
           - If unsuccessful, returns (False, error_message) where error_message
           is a string describing the error.
       Raises:
       - None. Exceptions are caught internally and handled with retries.

       Notes:
       - This function initializes a web driver, performs Twitter authentication,
         searches for a Twitter profile, and scrapes tweets from the profile page.
       - It uses Selenium WebDriver for web scraping and interacts with elements
         based on their XPATH on the Twitter web interface.
       - Retries are attempted for certain exceptions (NoSuchElementException,
         StaleElementReferenceException) up to MAX_EXCEPTION_RETRIES times.
       - Ensure proper setup of WebDriver and environment variables (like PAIDPROXY in settings)
         to match the environment requirements.
       """
    print_current_thread()
    print("web driver initializing")
    driver = (
        driver_initializer.initialize_paid_proxy()
        if settings.PAIDPROXY
        else driver_initializer.initialize_free_proxy()
    )
    data = []

    def scrap_data():
        nonlocal data  # Assuming data is defined in an outer scope
        articles = driver.find_elements(
            By.XPATH, "//div[@class='css-175oi2r' and @data-testid='cellInnerDiv']"
        )

        for article in articles:
            user_tag = article.find_element(
                By.XPATH,
                "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div/div/div/div[2]",
            ).text

            parts = user_tag.split("\n")
            username_with_at_symbol = parts[-1]

            timestamp = article.find_element(By.XPATH, "//time").get_attribute(
                "datetime"
            )
            tweet = article.find_element(
                By.XPATH, "//div[@data-testid='tweetText']"
            ).text
            reply = article.find_element(By.XPATH, '//*[@data-testid="reply"]').text
            retweet = article.find_element(
                By.XPATH, '//button[@data-testid="retweet"]//span'
            ).text
            likes = article.find_element(
                By.XPATH, '//button[@data-testid="like"]//span'
            ).text

            if not tweet_content_exists(data, tweet):
                data.append(
                    {
                        "Name": profile_name,
                        "UserTag": username_with_at_symbol,
                        "Timestamp": timestamp,
                        "TweetContent": tweet,
                        "Reply": reply,
                        "Retweet": retweet,
                        "Likes": likes,
                    }
                )

                print("data : ", data)
                print("posts scrap : ", len(data))

            if len(data) >= NUMBER_OF_POSTS:
                print(f"{NUMBER_OF_POSTS} posts scraped successfully")
                set_cache(full_url, data, timeout=CACHE_TIMEOUT)
                return save_data_and_return(data, profile_name)

        driver.execute_script("window.scrollBy(0, 200);")
        random_sleep()
        scrap_data()
    success, message = twitter_login_auth(driver)
    if not success:
        return message_json_response(
            status.HTTP_400_BAD_REQUEST, "error", "Twitter Authentication Error"
        )
    try:
        search_box = driver.find_element(
            By.XPATH, "//input[@data-testid='SearchBox_Search_Input']"
        )
        print("search_box element is found")
        action = ActionChains(driver)
        action.move_to_element(search_box).click().perform()
        for char in profile_name:
            action.send_keys(char).perform()
            sleep(0.1)  # Adjust delay as needed
        search_box.send_keys(Keys.ENTER)
        print(f"enter the search with value {profile_name}")
        random_sleep()
        people = driver.find_element(
            By.XPATH,
            "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[1]/div[1]/div[2]/nav/div/div["
            "2]/div/div[3]/a/div/div/span",
        )
        print("people element is found")
        people.click()
        print("click on people !!!!!!!!!!!!!!!!!!")
        random_sleep()
        WebDriverWait(driver, 60).until(
            ec.presence_of_element_located(
                (
                    By.XPATH,
                    "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/section/div/div/div["
                    "1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span/span[1]",
                )
            )
        )
        profile = driver.find_element(
            By.XPATH,
            "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/section/div/div/div["
            "1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span/span[1]",
        )
        print("profile element is found")
        profile.click()
        print("click on people profile !!!!!!!!!!!!!!!!!!")
        random_sleep()
        scrap_data()
        random_sleep()
        driver.quit()
        return save_data_and_return(data, profile_name)

    except NoSuchElementException as e:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_profile_tweets, profile_name, retry_count, type(e).__name__
        )
    except StaleElementReferenceException as ex:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_profile_tweets, profile_name, retry_count, type(ex).__name__
        )


@api_view(["GET"])
def get_tweeted_via_profile_name(request):
    """
       API endpoint to retrieve and scrape tweets from a Twitter profile based on profile_name.
       Uses multi-threading to handle the scraping process asynchronously.

       Parameters:
       - request (HttpRequest): Django request object containing query parameters.

       Returns:
       - JSON response with scraped tweet data or error message if profile_name is missing or scraping fails.
       """
    profile_name = request.query_params.get("Profile_name")
    full_url = request.build_absolute_uri()
    if not profile_name:
        return message_json_response(
            status.HTTP_400_BAD_REQUEST, "error", "Profile_name is required"
        )
    # cached_response = cache.get(profile_name)
    cached_response = get_cache(full_url)
    if cached_response:
        return save_data_and_return(cached_response, profile_name)
    with ThreadPoolExecutor(max_workers=MAX_THREAD_COUNT) as executor:
        future = executor.submit(scrape_profile_tweets, profile_name, 0, full_url)
        result = future.result()
    return result


def scrape_hashtag_tweets(hashtags, retry_count, full_url):
    """
       Scrapes tweets based on hashtags using a web driver initialized with proxy settings.

       Parameters:
       - hashtags (str): Hashtags to search for and scrape tweets.
       - retry_count (int): Number of retry attempts in case of exceptions.
       - full_url (str): Full URL of the current request for caching purposes.

       Returns:
       - JSON response with scraped tweet data or error message if scraping fails.
       """
    print_current_thread()
    print("web driver initializing")
    driver = (
        driver_initializer.initialize_paid_proxy()
        if settings.PAIDPROXY
        else driver_initializer.initialize_free_proxy()
    )
    data = []

    def scrap_data():
        nonlocal data
        articles = driver.find_elements(
            By.XPATH, "//div[@class='css-175oi2r' and @data-testid='cellInnerDiv']"
        )
        for article in articles:
            timestamp = article.find_element(By.XPATH, "//time").get_attribute(
                "datetime"
            )
            tweet = article.find_element(
                By.XPATH, "//div[@data-testid='tweetText']"
            ).text
            reply = article.find_element(By.XPATH, '//*[@data-testid="reply"]').text
            retweet = article.find_element(
                By.XPATH, '//button[@data-testid="retweet"]//span'
            ).text
            likes = article.find_element(
                By.XPATH, '//button[@data-testid="like"]//span'
            ).text

            if not tweet_content_exists(data, tweet):
                data.append(
                    {
                        "Name": hashtags,
                        "Timestamp": timestamp,
                        "TweetContent": tweet,
                        "Reply": reply,
                        "Retweet": retweet,
                        "Likes": likes,
                    }
                )
                print("data :", data)
                print("posts scrap : ", len(data))

        if len(data) >= NUMBER_OF_POSTS:
            set_cache(full_url, data, timeout=CACHE_TIMEOUT)
            return save_data_and_return(data, hashtags)
        driver.execute_script("window.scrollBy(0, 200);")
        sleep(5)
        scrap_data()

    success, message = twitter_login_auth(driver)
    if not success:
        return message_json_response(
            status.HTTP_400_BAD_REQUEST, "error", "Twitter Authentication Error"
        )
    try:
        search_box = driver.find_element(
            By.XPATH, "//input[@data-testid='SearchBox_Search_Input']"
        )
        print("search_box element is found")
        action = ActionChains(driver)
        action.move_to_element(search_box).click().perform()
        for char in hashtags:
            action.send_keys(char).perform()
            sleep(0.1)  # Adjust delay as needed
        search_box.send_keys(Keys.ENTER)
        print(f"enter the search with value {hashtags}")
        random_sleep()
        scrap_data()
    except NoSuchElementException as e:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_hashtag_tweets, hashtags, retry_count, type(e).__name__
        )
    except StaleElementReferenceException as ex:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_hashtag_tweets, hashtags, retry_count, type(ex).__name__
        )
    if "driver" in locals():
        driver.quit()
    return save_data_and_return(data, hashtags)


@api_view(["GET"])
def fetch_tweets_by_hash_tag(request):
    """
       Fetches tweets based on hashtags provided in the query parameters.

       Parameters:
       - request (Request): Django request object containing query parameters.

       Returns:
       - JSON response with scraped tweet data or error message if scraping fails.
       """
    hashtags = request.query_params.get("hashtags")
    full_url = request.build_absolute_uri()
    if not hashtags:
        return message_json_response(
            status.HTTP_400_BAD_REQUEST, "success", "hashtags is required"
        )
    # cached_response = cache.get(hashtags)
    cached_response = get_cache(full_url)
    if cached_response:
        return save_data_and_return(cached_response, hashtags)
    with ThreadPoolExecutor(max_workers=MAX_THREAD_COUNT) as executor:
        future = executor.submit(scrape_hashtag_tweets, hashtags, 0, full_url)
        result = future.result()
    return result


def scrape_trending_hashtags(trending, retry_count=0, full_url=None):
    """
      Scrapes trending hashtags from Twitter's explore section and caches the results.

      Args:
          trending (str): The trending topic or hashtag to scrape.
          retry_count (int, optional): Number of retry attempts in case of exceptions. Defaults to 0.
          full_url (str, optional): The full URL of the request for caching purposes. Defaults to None.

      Returns:
          tuple: A tuple indicating success status and JSON response.
                 - True if scraping and caching were successful, False otherwise.
                 - JSON response containing scraped trending topics.

      Raises:
          Exception: If scraping encounters unexpected errors, retries using `retry_exception`.

      Notes:
          This function initializes a web driver, navigates to Twitter's explore and trending sections,
          scrolls through the page to load all trending topics, extracts relevant information,
          and caches the scraped data using `set_cache`.

      """
    print_current_thread()
    print("web driver initializing")
    driver = (
        driver_initializer.initialize_paid_proxy()
        if settings.PAIDPROXY
        else driver_initializer.initialize_free_proxy()
    )
    success, message = twitter_login_auth(driver)
    if not success:
        return success, message
    try:
        explore_btn = driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div[2]/span",
        )
        print("explore element is found")
        explore_btn.click()
        print("explore element clicked")
        random_sleep()
        trending_btn = driver.find_element(
            By.XPATH,
            "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[1]/div[1]/div[2]/nav/div/div["
            "2]/div/div[2]/a/div/div/span",
        )
        print("trending element is found")
        trending_btn.click()
        print("trending element clicked")
        random_sleep()
        new_height = driver.execute_script("return document.body.scrollHeight")
        print("new_height found")
        last_height = driver.execute_script("return document.body.scrollHeight")
        print("last limit is found")

        while True:
            random_sleep()
            driver.execute_script("window.scrollBy(0, 1000);")
            random_sleep()
            if new_height == last_height:
                break
            last_height = new_height
        trending_topics = []
        trending_topics_elements = driver.find_elements(
            By.XPATH, '//*[@data-testid="cellInnerDiv"]'
        )
        print("trending element is found")
        for element in trending_topics_elements:
            text = element.text.split("\n")
            if len(text) >= 4:
                item = {
                    "id": text[0].strip(),
                    "category": text[2].split(" · ")[0].strip(),
                    "type": (
                        text[2].split(" · ")[1].strip()
                        if " · " in text[2]
                        else "Trending"
                    ),
                    "trending": text[3].strip(),
                    "posts": text[4].strip() if len(text) > 4 else "N/A",
                }
                trending_topics.append(item)
        json_response = trending_topics
        # cache.set(trending, json_response, timeout=60 * 15)
        set_cache(full_url, json_response, timeout=CACHE_TIMEOUT)
    except NoSuchElementException as e:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_trending_hashtags, trending, retry_count, type(e).__name__
        )
    except StaleElementReferenceException as ex:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_trending_hashtags, trending, retry_count, type(ex).__name__
        )
    if "driver" in locals():
        driver.quit()
    return True, json_response


@api_view(["GET"])
def get_trending_tweets(request):
    """
        Fetches and returns trending tweets from Twitter, either from cache or by scraping.
        Args:
            request (Request): Django HTTP request object containing query parameters.
        Returns:
            Response: JSON response containing trending tweets data fetched or scraped.
        Notes:
            This function checks if trending tweets data is available in cache using `get_cache`.
            If cached data exists, it returns the cached response using `save_data_and_return`.
            If no cached data is found, it initiates scraping of trending tweets using
            `scrape_trending_hashtags` in a ThreadPoolExecutor with max workers set to 5.
            It waits for the scraping to complete and handles the result:
            - If scraping is successful (`success=True`), it returns the scraped data using
              `save_data_and_return`.
            - If scraping fails (`success=False`), it returns an error response using
              `message_json_response`.

        """
    trending = "trending"
    # cached_response = cache.get(trending)
    full_url = request.build_absolute_uri()
    cached_response = get_cache(full_url)
    if cached_response:
        return save_data_and_return(cached_response, trending)
    with ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(scrape_trending_hashtags, trending, 0, full_url)
        success, result = future.result()
    if not success:
        return message_json_response(status.HTTP_400_BAD_REQUEST, "error", result)
    return save_data_and_return(result, trending)


def scrape_tweets_by_id(request, retry_count=0, full_url=None):
    """
       Scrapes Twitter tweets by their IDs and returns relevant information.

       Args:
           request (Request): Django HTTP request object containing query parameters:
               - user_name (str): The Twitter username associated with the tweets.
               - post_ids (str): Comma-separated string of tweet IDs to scrape.

           retry_count (int, optional): Number of retries attempted if scraping fails. Defaults to 0.
           full_url (str, optional): The full URL requested. Used for caching purposes. Defaults to None.

       Returns:
           tuple: A tuple containing two elements:
               - success (bool): True if scraping was successful, False otherwise.
               - data (list): List of dictionaries containing scraped tweet information.
                 Each dictionary includes the following keys:
                   - "username" (str): The Twitter username.
                   - "TweetContent" (str): The text content of the tweet.
                   - "views_count" (str): The count of views on the tweet.
                   - "timestamp" (str): The timestamp when the tweet was posted.
                   - "content_image" (str): The URL of any image attached to the tweet.
                   - "reply_count" (str): The count of replies to the tweet.
                   - "like_count" (str): The count of likes on the tweet.
                   - "repost_count" (str): The count of reposts (retweets) of the tweet.
                   - "bookmark_count" (str): The count of times the tweet was bookmarked.

       Notes:
           This function scrapes multiple tweets from Twitter based on their IDs.
           It initializes a web driver (paid or free proxy based on settings) and attempts
           to authenticate with Twitter using `twitter_login_auth`.
           For each tweet ID provided in the `post_ids` parameter, it constructs the tweet URL,
           navigates to the tweet page, and extracts relevant information such as tweet text,
           image URL (if any), engagement metrics, timestamp, and views count.
           The scraped data is stored in the `data` list and eventually cached using `set_cache`.
           If scraping encounters `NoSuchElementException` or `StaleElementReferenceException`,
           the function retries based on `retry_count`.
           Upon completion or error, the web driver is closed to free resources.
       """
    print_current_thread()
    print("web driver initializing")
    driver = (
        driver_initializer.initialize_paid_proxy()
        if settings.PAIDPROXY
        else driver_initializer.initialize_free_proxy()
    )
    success, message = twitter_login_auth(driver)
    if not success:
        return success, message
    try:
        data = []
        user_name = request.query_params.get("user_name")
        post_ids_str = request.query_params.get("post_ids")
        print("post_ids_str", post_ids_str)
        post_ids = post_ids_str.split(",")
        post_ids = [post_id.strip() for post_id in post_ids]
        for post_id in post_ids:
            twitter_url = f"https://x.com/{user_name}/status/{post_id}"
            print("twitter url ", twitter_url)
            driver.get(twitter_url)
            print("getting the data")
            random_sleep()
            tweet = driver.find_element(
                By.XPATH, "//div[@data-testid='tweetText']"
            ).text
            image_url = driver.find_element(
                By.CSS_SELECTOR, 'div[data-testid="tweetPhoto"] img'
            ).get_attribute("src")
            reply_count = (
                driver.find_element(By.CSS_SELECTOR, 'button[data-testid="reply"]')
                .find_element(
                    By.CSS_SELECTOR,
                    'span[data-testid="app-text-transition-container"] span',
                )
                .text
            )
            like_count = (
                driver.find_element(By.CSS_SELECTOR, 'button[data-testid="like"]')
                .find_element(
                    By.CSS_SELECTOR,
                    'span[data-testid="app-text-transition-container"] span',
                )
                .text
            )
            repost_count = (
                driver.find_element(By.CSS_SELECTOR, 'button[data-testid="retweet"]')
                .find_element(
                    By.CSS_SELECTOR,
                    'span[data-testid="app-text-transition-container"] span',
                )
                .text
            )
            bookmark_count = (
                driver.find_element(By.CSS_SELECTOR, 'button[data-testid="bookmark"]')
                .find_element(
                    By.CSS_SELECTOR,
                    'span[data-testid="app-text-transition-container"] span',
                )
                .text
            )
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")

            timestamp = driver.find_element(By.XPATH, "//time").get_attribute(
                "datetime"
            )
            views_count = driver.find_element(By.CSS_SELECTOR, "span.css-1jxf684").text

            data.append(
                {
                    "username": user_name,
                    "TweetContent": tweet,
                    "views_count": views_count,
                    "timestamp": timestamp,
                    "content_image": image_url,
                    "reply_count": reply_count,
                    "like_count": like_count,
                    "repost_count": repost_count,
                    "bookmark_count": bookmark_count,
                }
            )
            print("scrapping !!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
        # cache.set(f"get_by_id {user_name}", data, timeout=60 * 15)
        set_cache(full_url, data, timeout=CACHE_TIMEOUT)
    except NoSuchElementException as e:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_tweets_by_id, request, retry_count, type(e).__name__
        )
    except StaleElementReferenceException as ex:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrape_tweets_by_id, request, retry_count, type(ex).__name__
        )
    if "driver" in locals():
        driver.quit()
    return True, data


@api_view(["GET"])
def get_tweets_by_id(request):
    """
       Retrieves and caches Twitter tweets by their IDs associated with a specific user.

       Args:
           request (Request): Django HTTP request object containing query parameters:
               - user_name (str): The Twitter username associated with the tweets.
               - post_ids (str): Comma-separated string of tweet IDs to retrieve.

       Returns:
           JsonResponse: JSON response containing the retrieved tweet data.

       Notes:
           This function checks if the requested tweets for a specific user and tweet IDs
           are already cached. If cached data exists, it returns the cached response.
           If not cached, it spawns a background task using ThreadPoolExecutor to
           scrape the tweets using `scrape_tweets_by_id` function.

           The function ensures both `user_name` and `post_ids` query parameters are provided.
           Upon successful retrieval, the scraped data is cached for future requests using `set_cache`.

           If scraping encounters errors, it retries based on exception handling mechanisms in
           `scrape_tweets_by_id`. If retries fail, it returns an error response indicating the issue.

       Raises:
           HTTP_400_BAD_REQUEST: If either `user_name` or `post_ids` parameters are missing in the request.

       """
    user_name = request.query_params.get("user_name")
    full_url = request.build_absolute_uri()
    post_ids_str = request.query_params.get("post_ids")
    if not (user_name and post_ids_str):
        return message_json_response(
            status.HTTP_400_BAD_REQUEST,
            "error",
            "Both user_name and post_ids are required.",
        )
    # cached_response = cache.get(f"get_by_id {user_name}")
    cached_response = get_cache(full_url)
    if cached_response:
        return save_data_and_return(cached_response, user_name)
    with ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(scrape_tweets_by_id, request, 0, full_url)
        success, result = future.result()
    if not success:
        return message_json_response(status.HTTP_400_BAD_REQUEST, "error", result)
    return save_data_and_return(result, user_name)


def scrap_get_comments_for_tweet(request, retry_count=0, full_url=None):
    """
       Scrapes comments from Twitter tweets specified by user_name and post_ids.

       Args:
           request (Request): Django HTTP request object containing query parameters:
               - user_name (str): The Twitter username associated with the tweets.
               - post_ids (str): Comma-separated string of tweet IDs to retrieve comments from.
           retry_count (int, optional): Number of retries attempted in case of failure. Defaults to 0.
           full_url (str, optional): Full URL of the request, used for caching purposes. Defaults to None.

       Returns:
           tuple: A tuple indicating success or failure of the scraping operation and a JSON response.
               - If successful, returns (True, json_response).
               - If unsuccessful, returns (False, error_message).

       Notes:
           This function initializes a web driver and performs Twitter authentication.
           It retrieves tweet comments by visiting each tweet URL constructed from user_name and post_ids.
           Comments are scraped using a combination of scrolling the page and waiting for elements to load.
           Scraped comments are formatted and returned in a JSON response under 'comments' key.

           If scraping encounters errors such as NoSuchElementException or StaleElementReferenceException,
           it retries the operation based on the retry_count. If retries fail, it returns an error message.

           The function ensures the web driver is properly closed after scraping, even in case of errors.

       """
    print_current_thread()
    print("web driver initializing")
    driver = (
        driver_initializer.initialize_paid_proxy()
        if settings.PAIDPROXY
        else driver_initializer.initialize_free_proxy()
    )
    success, message = twitter_login_auth(driver)
    if not success:
        return success, message

    json_response = {
        "comments": []
    }  # Initialize json_response with a default empty list

    try:
        data = []
        user_name = request.query_params.get("user_name")
        post_ids_str = request.query_params.get("post_ids")
        print("post_ids_str", post_ids_str)
        post_ids = post_ids_str.split(",")
        post_ids = [post_id.strip() for post_id in post_ids]

        for post_id in post_ids:
            twitter_url = f"https://x.com/{user_name}/status/{post_id}"
            print("twitter url ", twitter_url)
            driver.get(twitter_url)
            print("getting the data")
            random_sleep()

            WebDriverWait(driver, 15).until(
                ec.presence_of_element_located((By.XPATH, "//*[@role='article']"))
            )

            while len(data) < NUMBER_OF_POSTS:
                driver.execute_script("window.scrollBy(0, 200);")
                sleep(5)

                elements = driver.find_elements(By.XPATH, "//*[@role='article']")

                for element in elements:
                    comment_text = element.text.strip()
                    if comment_text and {"comment": comment_text} not in data:
                        data.append({"comment": comment_text})

        if data:
            formatted_comments = []
            for item in data:
                comment_text = item["comment"].split("\n")
                try:
                    if len(comment_text) >= 8:
                        name = comment_text[0]
                        username = comment_text[1]
                        time = comment_text[3]
                        comment = comment_text[4]
                        likes = comment_text[5].split()[0]
                        views = comment_text[7]

                        formatted_comment = {
                            "Name": name,
                            "Username": username,
                            "Time": time,
                            "Comment": comment,
                            "Likes": likes,
                            "Views": views,
                        }

                        formatted_comments.append(formatted_comment)
                    else:
                        print(
                            f"Skipping item due to insufficient data: {item['comment']}"
                        )
                except IndexError as e:
                    print(f"Error processing item: {item['comment']}. Error: {str(e)}")

            json_response = {"comments": formatted_comments}
            set_cache(full_url, json_response, timeout=CACHE_TIMEOUT)

    except NoSuchElementException as e:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrap_get_comments_for_tweet, request, retry_count, type(e).__name__
        )

    except StaleElementReferenceException as ex:
        if "driver" in locals():
            driver.quit()
        return retry_exception(
            scrap_get_comments_for_tweet, request, retry_count, type(ex).__name__
        )

    finally:
        if "driver" in locals():
            driver.quit()

    return True, json_response


@api_view(["GET"])
def get_comments_for_tweets(request):
    """
       Retrieves comments for tweets associated with a given user_name and post_ids.

       Args:
           request (Request): Django HTTP request object containing query parameters:
               - user_name (str): The Twitter username associated with the tweets.
               - post_ids (str): Comma-separated string of tweet IDs to retrieve comments from.
           full_url (str): Full URL of the request, used for caching purposes.

       Returns:
           Response: JSON response containing retrieved comments for tweets.
               - If successful, returns comments data with HTTP 200 OK status.
               - If user_name or post_ids are missing, returns HTTP 400 BAD REQUEST.
               - If an error occurs during scraping or processing, returns HTTP 400 BAD REQUEST with error message.

       Notes:
           This function initiates scraping of comments from Twitter tweets based on provided user_name and post_ids.
           It checks if the requested data is cached; if not, it initiates a background thread for scraping using
           scrap_get_comments_for_tweet function.
           Upon successful scraping, the retrieved comments are formatted and cached using set_cache for future requests.
           Error handling includes cases of missing user_name or post_ids, as well as exceptions during scraping.

       """
    user_name = request.query_params.get("user_name")
    post_ids_str = request.query_params.get("post_ids")
    full_url = request.build_absolute_uri()
    if not (user_name and post_ids_str):
        return message_json_response(
            status.HTTP_400_BAD_REQUEST,
            "error",
            "Both user_name and post_ids are required.",
        )
    # cached_response = cache.get(data_)
    cached_response = get_cache(full_url)
    if cached_response:
        return save_data_and_return(cached_response, user_name)
    with ThreadPoolExecutor(max_workers=5) as executor:
        future = executor.submit(scrap_get_comments_for_tweet, request, 0, full_url)
        success, result = future.result()
    if not success:
        return message_json_response(status.HTTP_400_BAD_REQUEST, "error", result)
    return save_data_and_return(result, user_name)


# Cloudflare configuration......
@require_http_methods(["POST"])
def create_instance(request):
    instance_data = request.POST.get("instance_data")
    response = requests.post(
        f"{CLOUDFLARE_WORKER_URL}/create", json={"instance": instance_data}
    )
    return JsonResponse(response.json(), status=response.status_code)


@require_http_methods(["GET"])
def get_instance(request):
    response = requests.get(f"{settings.CLOUDFLARE_WORKER_URL}/get")
    return JsonResponse(response.json(), status=response.status_code)


@require_http_methods(["POST"])
def release_instance(request):
    instance_data = request.POST.get("instance_data")
    response = requests.post(
        f"{CLOUDFLARE_WORKER_URL}/release", json={"instance": instance_data}
    )
    return JsonResponse(response.json(), status=response.status_code)


@require_http_methods(["POST"])
def close_instance(request):
    instance_data = request.POST.get("instance_data")
    response = requests.post(
        f"{CLOUDFLARE_WORKER_URL}/close", json={"instance": instance_data}
    )
    return JsonResponse(response.json(), status=response.status_code)
