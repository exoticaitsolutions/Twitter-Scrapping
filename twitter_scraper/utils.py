import json
import os
import random
from time import sleep
from django.utils import timezone
from rest_framework import status
from typing import Optional, Dict
import undetected_chromedriver as uc
from django.core.cache import cache
from django.http import JsonResponse
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By


def get_mailinator_code(email):
    username = email.split("@")[0]
    url = f"https://www.mailinator.com/v4/public/inboxes.jsp?to={username}"

    # driver = webdriver.Chrome()
    driver = uc.Chrome(use_subprocess=False)
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")
    driver.maximize_window()
    driver.get(url)
    random_sleep()

    try:
        sleep(3)
        # Click the email item
        driver.find_element(
            By.XPATH,
            "/html/body/div/main/div[2]/div[3]/div/div[4]/div/div/table/tbody/tr/td[3]",
        ).click()
        random_sleep()

        # Get the element containing the code
        element = driver.find_element(
            By.XPATH, "//div[@class='fz-20 ff-futura-demi gray-color ng-binding']"
        ).text
        random_sleep()

        # Extract the code
        last = element.split()[-1]
        first = element.split()[0]
        print("element : ", element, first, last)
        code = first if first.isdigit() else last

        print(f"Code is: {code}")
        return code

    except NoSuchElementException:
        print("Element not found. Check if the class name is correct.")
        return None

    except TimeoutException:
        print("Timed out waiting for the element to be visible.")
        return None

    finally:
        driver.quit()


USER_CREDENTIALS = [
    {
        "full name": "Sunny",
        "username": "Sunny634164",
        "email": "sunnyexoticait@gmail.com",
        "password": "Sunny@123",
    },
    # {
    #     "full name": "MosleySeri72159",
    #     "username": "MosleySeri72159",
    #     "email": "xohik@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "Melvin Barber",
    #     "username": "MelvinBarb10693",
    #     "email": "zavow@mailinator.com",
    #     "password": "EF7T6TJwZnE9fakzJLiRfRFDNJuL",
    # },
    # {
    #     "full name": "Mariam Park",
    #     "username": "MariamPark98427",
    #     "email": "gipo@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "demetria63800",
    #     "username": "demetria63800",
    #     "email": "pifoga@mailinator.com",
    #     "password": "3TVNhFa2wJfhYq0",
    # },
    # {
    #     "full name": "JoelClay287888",
    #     "username": "JoelClay287888",
    #     "email": "gery@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "knight_may39057",
    #     "username": "knight_may39057",
    #     "email": "paro@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "ShaeleighT54515",
    #     "username": "ShaeleighT54515",
    #     "email": "kazoruzog@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "rocha_domi30885",
    #     "username": "rocha_domi30885",
    #     "email": "xawi@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "jemima_rui69057",
    #     "username": "jemima_rui69057",
    #     "email": "noxy@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "ChristianF88294",
    #     "username": "ChristianF88294",
    #     "email": "nutihidyf@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "ConstanceF3888",
    #     "username": "ConstanceF3888",
    #     "email": "dasavoxoga@mailinator.com",
    #     "password": "asdf123@",
    # },
    # {
    #     "full name": "WeissJorde72850",
    #     "username": "WeissJorde72850",
    #     "email": "racibezasa@mailinator.com",
    #     "password": "asdf123@",
    # },
]


def random_sleep(min_time=6, max_time=10):
    """
    Sleeps for a random duration between the specified minimum and maximum times.

    Parameters:
        min_time (float, optional): The minimum sleep time in seconds. Defaults to 1.
        max_time (float, optional): The maximum sleep time in seconds. Defaults to 10.

    Returns:
        None

    Example:
        >>> random_sleep(min_time=2, max_time=5)
        # Output example: --> Now sleeping for 3.78 seconds
    """
    sleep_time = random.uniform(min_time, max_time)
    print(f"--> Now sleeping for {sleep_time:.2f} seconds")
    sleep(sleep_time)


def type_slowly(element, text, delay=0.1):
    """
    Types text slowly into a specified web element.

    Parameters:
        element (WebElement): The web element where the text will be typed.
        text (str): The text to be typed into the element.
        delay (float, optional): The delay (in seconds) between typing each character.
            Defaults to 0.1 seconds.

    Returns:
        None
    """
    for char in text:
        element.send_keys(char)
        sleep(delay)


# driver = uc.Chrome(headless=True, use_subprocess=False)


def twitter_login_auth(driver):
    """
    Perform Twitter login authentication.
    Returns:
        tuple: A tuple containing a boolean indicating success or failure of the login attempt,
               and a string with a message indicating the outcome.
    """
    # Select a random set of credentials
    credentials = random.choice(USER_CREDENTIALS)
    username_value = credentials["username"]
    print("username is", username_value)
    password_value = credentials["password"]
    print("password is", "*" * len(password_value))
    email = credentials["email"]
    print("email : ", email)
    driver.get("https://twitter.com/i/flow/login")
    random_sleep()
    try:
        username = driver.find_element(By.XPATH, "//input[@name='text']")
        actions = ActionChains(driver)
        actions.move_to_element(username).click().perform()
        type_slowly(username, username_value)
        random_sleep()
        print("Username element found and value sent successfully.")
    except NoSuchElementException:
        return False, "Username element not found"
    try:
        next_button = driver.find_element(By.XPATH, "//span[contains(text(),'Next')]")
        actions.move_to_element(next_button).click().perform()
        print("Next button element found and clicked successfully.")
        random_sleep()
    except NoSuchElementException:
        return False, "Next button element not found"

    try:
        password = driver.find_element(By.XPATH, "//input[@name='password']")
        random_sleep()
        actions.move_to_element(password).click().perform()
        type_slowly(password, password_value)
        print("Password element found and value sent successfully.")
        random_sleep()
    except NoSuchElementException:
        return False, "Password element not found"

    # Locate and click the "Log in" button
    log_in = driver.find_element(By.XPATH, "//span[contains(text(),'Log in')]")
    actions.move_to_element(log_in).click().perform()
    print("Log in button found and clicked successfully.")
    random_sleep()
    try:
        # Attempt to find the code input box for authentication
        code_input_box = driver.find_element(By.XPATH, "//input[@inputmode='text']")
        print("Code input box found for authentication")
        # Get verification code from Mailinator
        code = get_mailinator_code(email)
        code_input_box.send_keys(code)  # Enter the verification code
        random_sleep()
        print("confirmation code writen")
        # Click the next button to proceed with authentication
        driver.find_element(
            By.XPATH, "//div[@class='css-175oi2r r-b9tw7p']//button"
        ).click()
        random_sleep()
    except BaseException:
        # If code input box is not found, handle the scenario where email input box is displayed for authentication
        email_input_box = driver.find_element(By.XPATH, "//input[@inputmode='email']")
        print("Email input box found for authentication")
        email_input_box.send_keys(email)  # Enter the email address
        random_sleep()
        driver.find_element(
            By.XPATH, "//div[@class='css-175oi2r r-b9tw7p']//button"
        ).click()
        random_sleep()
    finally:
        # Return success status and message indicating successful Twitter login
        return True, "Twitter login successful"


def message_json_response(
    code: int, error_type: str, error_message: str, data: Optional[Dict] = None
) -> JsonResponse:
    """
    Create a JSON response with the provided code, error type, error message, and optional data.
    Parameters:
    - code (int): The HTTP status code to be returned.
    - error_type (str): The type of error.
    - error_message (str): The error message.
    - data (dict, optional): Additional data to include in the response.
    Returns:
    - JsonResponse: A JSON response containing the provided data and status code.
    """
    response_data = {
        "code": code,
        "type": error_type,
        "message": error_message,
    }
    if data:
        response_data["data"] = data

    return JsonResponse(response_data, status=code, json_dumps_params=dict(indent=2))


def save_data_in_directory(folder_name, file_name, json_data: dict):
    """
    Saves JSON data in a specified directory with the provided file name.
    If the specified directory does not exist, it creates the directory.
    Parameters:
    - folder_name (str): The name of the directory where the data will be saved.
    - file_name (str): The name of the file to be created (without the extension).
    - json_data (dict): The JSON data to be saved.
    Returns:
    - None
    Example:
    json_data = {"key": "value"}
    save_data_in_directory("my_folder", "my_file", json_data)
    This will create a file named "my_file.json" inside the "my_folder" directory and save the JSON data in it.
    """
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)
    file_path = os.path.join(folder_name, f"{file_name}.json")
    print(file_path)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    return True


def tweet_content_exists(tweets, tweet_content):
    return any(tweet.get("TweetContent") == tweet_content for tweet in tweets)


def set_cache(key, value, timeout=None):
    """
    Set a value in the cache.
    :param timeout:
    :param key: Cache key
    :param value: Value to cache    :param timeout:  timeout in seconds. Defaults to the default timeout if None.
    """
    print(
        "Setting the key = ",
        key,
        " and value = ",
        value,
        " for timeout = ",
        timeout,
        " in Redis cache.",
    )
    cache.set(key, value, timeout)


def get_cache(key, default=None):
    return cache.get(key, default)


def save_data_and_return(data, data_append):
    save_data_in_directory(f"json_Response/{timezone.now().date()}/", data_append, data)
    return message_json_response(
        status.HTTP_200_OK, "success", "Tweets retrieved successfully", data=data
    )
