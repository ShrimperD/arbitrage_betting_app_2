from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time

def place_bet_draftkings(username, password, bet_details):
    # Set up Chrome driver
    options = webdriver.ChromeOptions()
    options.add_argument("--headless")  # Run in headless mode
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        # Log in to DraftKings
        driver.get("https://myaccount.draftkings.com/login?intendedSiteExp=US-KS-SB")
        time.sleep(5)  # Wait for page to load

        # Wait for the username field to appear
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "login-username-input")))

        # Enter username and password
        driver.find_element(By.ID, "login-username-input").send_keys(username)
        driver.find_element(By.ID, "login-password-input").send_keys(password)

        # Click the login button
        driver.find_element(By.XPATH, "//*[@id='login-submit']/div").click()
        time.sleep(5)  # Wait for login to complete

        # Navigate to the event page
        driver.get(bet_details['url'])
        time.sleep(5)  # Wait for page to load

        # Place the bet
        driver.find_element(By.CSS_SELECTOR, "input[data-testid='betslip-wager-box-input']").send_keys(bet_details['stake'])
        driver.find_element(By.CLASS_NAME, "place-bet-button").click()
        time.sleep(5)  # Wait for bet to be placed

        print("Bet placed successfully on DraftKings!")
    except Exception as e:
        print(f"Error placing bet on DraftKings: {e}")
    finally:
        driver.quit()

# Example usage
bet_details = {
    'url': 'https://www.draftkings.com/bet-on/sports/event/12345',  # Replace with actual event URL
    'stake': 5  # Bet amount
}
place_bet_draftkings("dbrillhart620@gmail.com", "MadyMasonEma0!", bet_details)