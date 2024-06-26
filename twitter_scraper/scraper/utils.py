import random
from typing import Optional, Dict
from django.http import JsonResponse
import os
import json
from time import sleep
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException

USER_CREDENTIALS = [
    {"username": "ExoticaLtd","email":"webbdeveloper24@gmail.com", "password": "S5Us3/)pT$.H#yy"},
    {"username": "demetria63800", "email": "pifoga@mailinator.com", "password": "3TVNhFa2wJfhYq0"},
]


def random_sleep(min_time=1, max_time=10):
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

    Example:
        Assuming `element` is a Selenium WebElement representing a text input field:
        >>> type_slowly(element, "Hello, world!", delay=0.05)
        # This would type "Hello, world!" into the text input field, with a delay of 0.05 seconds between each character.
    """
    for char in text:
        element.send_keys(char)
        sleep(delay)


def twitterLogin_auth(driver):
    """
    Perform Twitter login authentication.
    Returns:
        tuple: A tuple containing a boolean indicating success or failure of the login attempt,
               and a string with a message indicating the outcome.
    """
    # Select a random set of credentials
    credentials = random.choice(USER_CREDENTIALS)
    username_value = credentials['username']
    print('username is', username_value)
    password_value = credentials['password']
    print('username is', '*' * len(password_value))
    driver.get('https://twitter.com/i/flow/login')
    sleep(10)
    try:
        # Locate the username input field and type the username
        username = driver.find_element(By.XPATH, "//input[@name='text']")
        random_sleep()
        actions = ActionChains(driver)
        actions.move_to_element(username).click().perform()
        type_slowly(username, username_value)
        print("Username element found and value sent successfully.")
    except NoSuchElementException:
        return False, "Username element not found"

    try:
        # Locate and click the "Next" button
        next_button = driver.find_element(By.XPATH, "//span[contains(text(),'Next')]")
        sleep(10)
        actions.move_to_element(next_button).click().perform()
        print("Next button element found and clicked successfully.")
        sleep(6)
    except NoSuchElementException:
        return False, "Next button element not found"

    try:
        # Locate the password input field and type the password
        password = driver.find_element(By.XPATH, "//input[@name='password']")
        random_sleep()
        actions.move_to_element(password).click().perform()
        type_slowly(password, password_value)
        print("Password element found and value sent successfully.")
        sleep(6)
    except NoSuchElementException:
        return False, "Password element not found"

    try:
        # Locate and click the "Log in" button
        log_in = driver.find_element(By.XPATH, "//span[contains(text(),'Log in')]")
        random_sleep()
        actions.move_to_element(log_in).click().perform()
        print("Log in button found and clicked successfully.")
        sleep(6)
    except NoSuchElementException:
        return False, "Log in button element not found"

    return True, "Twitter login successful"


# Example usage
if __name__ == "__main__":
    driver = webdriver.Chrome()  # Use your WebDriver of choice
    success, message = twitterLogin_auth(driver)
    print(message)
    driver.quit()


def message_json_response(code: int, error_type: str, error_message: str, data: Optional[Dict] = None) -> JsonResponse:
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
    with open(file_path, "w", encoding='utf-8') as f:
        json.dump(json_data, f, ensure_ascii=False, indent=4)
    return True
