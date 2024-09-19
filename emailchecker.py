import time
import requests
from pymongo import MongoClient
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

class EmailChecker:
    def __init__(self, github_token):
        self.listEmails = []
        self.github_token = github_token  # Store GitHub token for API requests

    def requestDataFromApi(self):
        try:
            responseApiEmails = requests.get("https://www.datos.gov.co/resource/jtnk-dmga.json")
            responseApiEmails.raise_for_status()  # Raise an error for bad responses
            dataJson = responseApiEmails.json()
            for entry in dataJson:
                self.listEmails.append(entry.get("email_address"))
        except requests.RequestException as e:
            print(f"Error fetching data from API: {e}")

    def validate_email(self, email):
        validation_api_url = f"https://mailscrap.com/api/verifier-lookup/{email}"
        try:
            responseEmail = requests.get(validation_api_url)
            responseEmail.raise_for_status()  # Raise an error for bad responses
            dataEmailsJson = responseEmail.json()
            return dataEmailsJson.get("deliverable", False)
        except requests.RequestException as e:
            print(f"Error validating email {email}: {e}")
            return False

    def check_github_account(self, email):
        url = f"https://api.github.com/users/{email.split('@')[0]}"  # Check user by username
        headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json"  # Standard GitHub API response
        }
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                return True  # Email corresponds to a GitHub user
            elif response.status_code == 404:
                return False  # User not found
            else:
                print(f"Error checking GitHub for {email}: {response.status_code}")
                return False
        except requests.RequestException as e:
            print(f"Error occurred while checking {email} on GitHub: {e}")
            return False

def process_email(email_checker, email):
    if email_checker.validate_email(email):
        if email_checker.check_github_account(email):
            return email
    return None

def save_data_to_mongodb(data, mongodb_uri, db_name, collection_name):
    try:
        client = MongoClient(mongodb_uri)
        db = client[db_name]
        collection = db[collection_name]
        collection.insert_many(data)
        print("Data saved to MongoDB Atlas successfully.")
    except Exception as e:
        print(f"Error saving data to MongoDB Atlas: {e}")

def main():
    # MongoDB and GitHub token details
    mongodb_uri = "mongodb+srv://MongodbFabian:Admin777@cluster0.utsby.mongodb.net/"  # Replace with your MongoDB Atlas URI
    db_name = "correos_phishing"  # Replace with your database name
    collection_name = "correos"
    github_token = "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"  # Replace with your GitHub token

    # Create instance of EmailChecker
    checker = EmailChecker(github_token)
    
    # Fetch data from the government API
    checker.requestDataFromApi()

    # Use ThreadPoolExecutor to speed up the validation process
    deliverable_and_github_emails = []
    
    print("Cargando...")
    with ThreadPoolExecutor(max_workers=10) as executor:  # Adjust max_workers as needed
        futures = {executor.submit(process_email, checker, email): email for email in checker.listEmails}
        
        # Display progress bar
        for future in tqdm(as_completed(futures), total=len(futures)):
            result = future.result()
            if result:
                deliverable_and_github_emails.append(result)

    # Print deliverable emails with GitHub accounts
    print("Deliverable emails with GitHub accounts:")
    for email in deliverable_and_github_emails:
        print(email)

    # Prepare data for MongoDB
    processed_data = [{"email": email, "is_valid": True} for email in deliverable_and_github_emails]

    # Save data to MongoDB Atlas
    save_data_to_mongodb(processed_data, mongodb_uri, db_name, collection_name)

if __name__ == "__main__":
    main()
