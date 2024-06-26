from django.utils import timezone
import threading
from rest_framework import status
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from rest_framework.decorators import api_view
from concurrent.futures import ThreadPoolExecutor
from .serializers import TwitterProfileSerializers, TweetHashtagSerializer, TweetUrlSerializer
from .utils import twitterLogin_auth, message_json_response, save_data_in_directory, random_sleep
from .web_driver import initialize_driver
from time import sleep


def print_current_thread():
    """
    Print the name of the current thread.

    This function retrieves the current thread using threading.current_thread()
    and prints its name.

    Example:
        print_current_thread()

    Output:
        ---------- Current Thread: MainThread
    """
    current_thread = threading.current_thread()
    print("---------- Current Thread:", current_thread.name)


# Function to retry a given block of code
def retry(func, retries=3):
    """
    Retry executing a function a specified number of times.

    Args:
        func (callable): The function to be executed.
        retries (int, optional): The maximum number of retries. Defaults to 3.

    Raises:
        StaleElementReferenceException: If the maximum number of retries is exceeded.

    Returns:
        Any: The return value of the function 'func'.

    Example:
        To use this function, define a function to retry and pass it as an argument.
        For instance:

        ```python
        def my_function():
            # Your function implementation
            pass

        retry(my_function, retries=5)
        ```

    """
    for attempt in range(retries):
        try:
            return func()
        except StaleElementReferenceException:
            print("StaleElementReferenceException caught. Retrying...")
            random_sleep()
        except NoSuchElementException:
            print("NoSuchElementException caught. Aborting retry.")
            raise
    raise StaleElementReferenceException("Exceeded maximum number of retries.")


# Function to scrape tweets from a profile
def scrape_profile_tweets(profile_name):
    print_current_thread()
    driver = initialize_driver()
    # Authenticate with Twitter
    success, message = twitterLogin_auth(driver)
    if not success:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'Twitter Authentication Error')
    sleep(20)
    try:
        random_sleep()
        search_box = driver.find_element(By.XPATH, "//input[@data-testid='SearchBox_Search_Input']")
        action = ActionChains(driver)
        sleep(9)
        action.move_to_element(search_box).click().perform()
        for char in profile_name:
            action.send_keys(char).perform()
            sleep(0.1)  # Adjust delay as needed
        search_box.send_keys(Keys.ENTER)
        sleep(20)
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'search_box Element not found')

    try:
        people = driver.find_element(By.XPATH,
                                     "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[3]/a/div/div/span")
        people.click()
        sleep(15)
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'people Element not found')

    try:
        WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.XPATH,
                                                                        "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span/span[1]")))
        profile = driver.find_element(By.XPATH,
                                      "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/section/div/div/div[1]/div/div/button/div/div[2]/div[1]/div[1]/div/div[1]/a/div/div[1]/span/span[1]")
        profile.click()
        random_sleep()
    except (NoSuchElementException, StaleElementReferenceException):
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'profile Element not found')

    data = []
    try:
        articles = driver.find_elements(By.CLASS_NAME, 'css-175oi2r')
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'articles Element not found')

    # Scrape tweets until the desired number is reached or no more tweets are available
    while True:
        for _ in articles:
            user_tag = driver.find_element(By.XPATH,
                                           "//*[@id='react-root']/div/div/div[2]/main/div/div/div/div[1]/div/div[3]/div/div/div/div/div[2]").text
            timestamp = driver.find_element(By.XPATH, "//time").get_attribute('datetime')
            tweet = driver.find_element(By.XPATH, "//div[@data-testid='tweetText']").text
            reply = driver.find_element(By.XPATH, f'//*[@data-testid="reply"]').text
            retweet = driver.find_element(By.XPATH, '//button[@data-testid="retweet"]//span').text
            likes = driver.find_element(By.XPATH, '//button[@data-testid="like"]//span').text
            data.append({
                "Name": profile_name,
                "UserTag": user_tag,
                "Timestamp": timestamp,
                "TweetContent": tweet,
                "Reply": reply,
                "Retweet": retweet,
                "Likes": likes
            })
            driver.execute_script('window.scrollTo(0,document.body.scrollHeight);')
            if len(data) > 5:
                break
        break

    # Save the scraped data to a directory
    save_data_in_directory(f"Json_Response/{timezone.now().date()}/", profile_name, data)
    driver.quit()
    return message_json_response(status.HTTP_200_OK, 'success', 'Tweets retrieved successfully', data=data)


@api_view(["POST"])
def get_tweeted_via_profile_name(request):
    serializer = TwitterProfileSerializers(data=request.data)
    profile_name = request.data.get("Profile_name")
    if serializer.is_valid():
        # Use ThreadPoolExecutor to run the scrape_profile_tweets function in a separate thread
        with ThreadPoolExecutor(max_workers=5) as executor:
            future = executor.submit(scrape_profile_tweets, profile_name)
            result = future.result()
        return result

    return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', serializer.errors)


# Function to scrape tweets based on hashtags
def scrape_hashtag_tweets(hashtags):
    print_current_thread()
    driver = initialize_driver()

    # Authenticate with Twitter
    success, message = twitterLogin_auth(driver)
    if not success:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'Twitter Authentication Failed')

    try:
        random_sleep()
        search_box = driver.find_element(By.XPATH, "//input[@data-testid='SearchBox_Search_Input']")
        search_box.send_keys(hashtags)
        search_box.send_keys(Keys.ENTER)
        sleep(20)
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'search_box element not found')
    except StaleElementReferenceException:
        # If the element is stale, re-locate it and try again
        print("Element is stale. Retrying...")

    data = []
    try:
        articles = driver.find_elements(By.CLASS_NAME, 'css-175oi2r')
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'articles element not found')
    except StaleElementReferenceException:
        # If the element is stale, re-locate it and try again
        print("Element is stale. Retrying...")

    try:
        # Scrape tweets until the desired number is reached or no more tweets are available
        while True:
            for article in articles:
                timestamp = driver.find_element(By.XPATH, "//time").get_attribute('datetime')
                tweet = driver.find_element(By.XPATH, "//div[@data-testid='tweetText']").text
                reply = driver.find_element(By.XPATH, f'//*[@data-testid="reply"]').text
                retweet = driver.find_element(By.XPATH, '//button[@data-testid="retweet"]//span').text
                likes = driver.find_element(By.XPATH, '//button[@data-testid="like"]//span').text
                data.append({
                    "Timestamp": timestamp,
                    "TweetContent": tweet,
                    "Reply": reply,
                    "Retweet": retweet,
                    "Likes": likes
                })
                driver.execute_script('window.scrollTo(0,document.body.scrollHeight);')
                if len(data) > 5:
                    break
            break
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'articles element not found')
    except StaleElementReferenceException:
        # If the element is stale, re-locate it and try again
        print("Element is stale. Retrying...")

    # Save the scraped data to a directory
    save_data_in_directory(f"Json_Response/{timezone.now().date()}/", hashtags, data)
    driver.quit()
    return message_json_response(status.HTTP_200_OK, 'success', 'Tweets retrieved successfully', data=data)


@api_view(["POST"])
def fetch_tweets_by_hash_tag(request):
    serializer = TweetHashtagSerializer(data=request.data)
    hashtags = request.data.get("hashtags")
    if serializer.is_valid():
        # Use ThreadPoolExecutor to run the scrape_hashtag_tweets function in a separate thread
        with ThreadPoolExecutor(max_workers=5) as executor:
            future = executor.submit(scrape_hashtag_tweets, hashtags)
            result = future.result()
        return result
    return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', serializer.errors)


# Function to scrape trending hashtags
def scrape_trending_hashtags(request):
    print_current_thread()
    driver = initialize_driver()

    # Authenticate with Twitter
    success, message = twitterLogin_auth(driver)
    if not success:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'Twitter Authentication Failed')

    try:
        random_sleep()
        explore_btn = driver.find_element(By.XPATH,
                                          "/html/body/div[1]/div/div/div[2]/header/div/div/div/div[1]/div[2]/nav/a[2]/div/div[2]/span")
        explore_btn.click()
        random_sleep()
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'explore element not found')

    try:
        trending_btn = driver.find_element(By.XPATH,
                                           "/html/body/div[1]/div/div/div[2]/main/div/div/div/div[1]/div/div[1]/div[1]/div[2]/nav/div/div[2]/div/div[2]/a/div/div/span")
        trending_btn.click()
        random_sleep()
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'trending element not found')

    # Scroll to the bottom of the page to load more content
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        random_sleep()
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    try:
        trending_topics_elements = driver.find_elements(By.XPATH, '//*[@data-testid="cellInnerDiv"]')
    except NoSuchElementException:
        return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'trending_topics_elements not found')

    trending_topics = []
    for element in trending_topics_elements:
        text = element.text.split('\n')
        if len(text) >= 4:
            item = {
                "id": text[0].strip(),
                "category": text[2].split(' · ')[0].strip(),
                "type": text[2].split(' · ')[1].strip() if ' · ' in text[2] else "Trending",
                "trending": text[3].strip(),
                "posts": text[4].strip() if len(text) > 4 else "N/A"
            }
            trending_topics.append(item)

    # Save the scraped data to a directory
    save_data_in_directory(f"Json_Response/{timezone.now().date()}/", "Trending", trending_topics)
    driver.quit()
    return message_json_response(status.HTTP_200_OK, 'success', 'Trending hashtags retrieved successfully',
                                 data=trending_topics)


@api_view(["get"])
def get_trending_tweets(request):
    """
    Function to get trending tweets by scraping Twitter for trending hashtags.

    Args:
        request (HttpRequest): The HTTP request object containing the request data.

    Returns:
        JSONResponse: A JSON response containing the scraped trending tweets data or an error message.
    """

    # Use ThreadPoolExecutor to run the scrape_trending_hashtags function in a separate thread
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit the scrape_trending_hashtags function with the request data as argument
        future = executor.submit(scrape_trending_hashtags, request)

        # Get the result of the future task
        result = future.result()

    # Return the result as a JSON response
    return result


def scrape_comments_for_tweets(request):
    """
    Function to scrape comments for tweets from Twitter.

    Args:
        request (HttpRequest): The HTTP request object containing the tweet data.

    Returns:
        JSONResponse: A JSON response containing the scraped comments data or error message.
    """

    # Validate the incoming request data using the TweetUrlSerializer
    serializer = TweetUrlSerializer(data=request.data)
    if serializer.is_valid():
        # Print the current working thread
        print_current_thread()

        # Initialize the WebDriver
        driver = initialize_driver()

        # Extract post IDs from the request data
        post_ids = request.data.get('post_ids')

        # Authenticate with Twitter
        success, message = twitterLogin_auth(driver)
        if success:
            # Add a random sleep for realistic behavior
            random_sleep()

        # Initialize an empty list to store the scraped data
        data = []

        # Iterate over each post ID
        for post_id in post_ids:
            print(f'user_name=', request.data.get('user_name'))
            print(f'post_id=', post_id)
            # Construct the URL of the tweet to scrape comments from
            twitter_url = f"https://x.com/{request.data.get('user_name')}/status/{post_id}"

            # Load the tweet URL in the browser
            driver.get(twitter_url)
            print(f'Twitter_url=', twitter_url)

            # Add another random sleep for realistic behavior
            random_sleep()

            try:
                # Find elements corresponding to tweets
                driver.find_elements(By.CLASS_NAME, 'css-175oi2r')
            except NoSuchElementException:
                # Return an error response if the tweet elements are not found
                return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'tweet_elements element not found')

            # Extract relevant information from the tweet elements
            tweet = driver.find_element(By.XPATH, "//div[@data-testid='tweetText']").text
            image_url = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetPhoto"] img').get_attribute('src')
            reply_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="reply"]').find_element(
                By.CSS_SELECTOR,
                'span[data-testid="app-text-transition-container"] span').text
            like_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="like"]').find_element(
                By.CSS_SELECTOR,
                'span[data-testid="app-text-transition-container"] span').text
            repost_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="retweet"]').find_element(
                By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"] span').text
            bookmark_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="bookmark"]').find_element(
                By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"] span').text
            driver.execute_script('window.scrollTo(0,document.body.scrollHeight);')
            timestamp = driver.find_element(By.XPATH, "//time").get_attribute('datetime')
            views_count = driver.find_element(By.CSS_SELECTOR, 'span.css-1jxf684').text

            # Append the extracted data to the list
            data.append({
                "username": request.data.get('user_name'),
                "TweetContent": tweet,
                "views_count": views_count,
                "timestamp": timestamp,
                "content_image": image_url,
                "reply_count": reply_count,
                "like_count": like_count,
                "repost_count": repost_count,
                "bookmark_count": bookmark_count
            })

        # Save the scraped data in a directory
        save_data_in_directory(f"Json_Response/{timezone.now().date()}/", request.data.get('user_name'), data)

        # Return a success response with the scraped data
        return message_json_response(status.HTTP_200_OK, 'error', 'tweets get  successFully', data=data)

    # Return an error response if the request data is invalid
    return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', serializer.errors)


@api_view(["POST"])
def get_comments_for_tweets(request):
    """
    Endpoint to asynchronously scrape comments for tweets from Twitter.

    Args:
        request (HttpRequest): The HTTP request object containing the tweet data.

    Returns:
        JSONResponse: A JSON response containing the scraped comments data or error message.
    """

    # Use ThreadPoolExecutor to run the scrape_comments_for_tweets function in a separate thread
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit the scrape_comments_for_tweets function to the executor with the request object as argument
        future = executor.submit(scrape_comments_for_tweets, request)

        # Wait for the function to complete and retrieve the result
        result = future.result()

    # Return the result obtained from scraping comments
    return result


def scrape_tweets_by_url(request):
    """
    Endpoint to scrape tweets from Twitter based on provided post URLs.

    Args:
        request (HttpRequest): The HTTP request object containing the data to be scraped.

    Returns:
        JSONResponse: A JSON response containing the scraped tweet data or error message.
    """
    # Deserialize request data using TweetUrlSerializer
    serializer = TweetUrlSerializer(data=request.data)

    # Check if serializer data is valid
    if serializer.is_valid():
        # Print the current working thread
        print_current_thread()

        # Initialize the Selenium WebDriver
        driver = initialize_driver()

        # Extract post IDs from the request data
        post_ids = request.data.get('post_ids')

        # Authenticate with Twitter and check if authentication is successful
        success, message = twitterLogin_auth(driver)
        if success:
            # Introduce a random sleep to simulate human-like behavior
            random_sleep()

        # Initialize an empty list to store scraped tweet data
        data = []

        # Iterate over each post ID
        for post_id in post_ids:
            # Construct the Twitter URL for the post using the username and post ID
            twitter_url = f"https://x.com/{request.data.get('user_name')}/status/{post_id}"

            # Load the Twitter URL in the WebDriver
            driver.get(twitter_url)

            # Introduce a random sleep to simulate human-like behavior
            random_sleep()

            try:
                # Find tweet elements
                tweet_elements = driver.find_elements(By.CLASS_NAME, 'css-175oi2r')
            except NoSuchElementException:
                # If tweet elements are not found, return a JSON response with an error message
                return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', 'tweet_elements element not found')

            # Extract various attributes of the tweet
            tweet = driver.find_element(By.XPATH, "//div[@data-testid='tweetText']").text
            image_url = driver.find_element(By.CSS_SELECTOR, 'div[data-testid="tweetPhoto"] img').get_attribute('src')
            reply_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="reply"]').find_element(
                By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"] span').text
            like_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="like"]').find_element(
                By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"] span').text
            repost_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="retweet"]').find_element(
                By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"] span').text
            bookmark_count = driver.find_element(By.CSS_SELECTOR, 'button[data-testid="bookmark"]').find_element(
                By.CSS_SELECTOR, 'span[data-testid="app-text-transition-container"] span').text

            # Scroll to the bottom of the page to load additional content
            driver.execute_script('window.scrollTo(0,document.body.scrollHeight);')

            # Extract timestamp and views count
            timestamp = driver.find_element(By.XPATH, "//time").get_attribute('datetime')
            views_count = driver.find_element(By.CSS_SELECTOR, 'span.css-1jxf684').text

            # Append scraped data to the list
            data.append({
                "username": request.data.get('user_name'),
                "TweetContent": tweet,
                "views_count": views_count,
                "timestamp": timestamp,
                "content_image": image_url,
                "reply_count": reply_count,
                "like_count": like_count,
                "repost_count": repost_count,
                "bookmark_count": bookmark_count
            })

        # Save the scraped data to a directory
        save_data_in_directory(f"Json_Response/{timezone.now().date()}/", request.data.get('user_name'), data)

        # Return a JSON response with success message and scraped data
        return message_json_response(status.HTTP_200_OK, 'success', 'Tweets retrieved successfully', data=data)

    # If serializer data is not valid, return a JSON response with serializer errors
    return message_json_response(status.HTTP_400_BAD_REQUEST, 'error', serializer.errors)


@api_view(["POST"])
def get_tweets_by_id(request):
    """
    Endpoint to asynchronously scrape tweets from Twitter based on provided post URLs.

    Args:
        request (HttpRequest): The HTTP request object containing the data to be scraped.

    Returns:
        JSONResponse: A JSON response containing the scraped tweet data or error message.
    """

    # Use ThreadPoolExecutor to run the scrape_tweets_by_url function in a separate thread
    with ThreadPoolExecutor(max_workers=5) as executor:
        # Submit the scrape_tweets_by_url function to the executor with the request object as argument
        future = executor.submit(scrape_tweets_by_url, request)

        # Wait for the function to complete and retrieve the result
        result = future.result()

    # Return the result obtained from scraping tweets
    return result
