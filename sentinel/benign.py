"""Hand-written harmless, instruction-shaped sentences.

These are the hard negatives: text that *sounds* like a command but is ordinary
document content (recipes, manuals, admin emails). Train and test lists cover
different domains so the false-positive test is not memorised.
"""

BENIGN_TRAIN = [
    # recipes
    "Preheat the oven to 180°C and grease a baking tray.",
    "Stir the sauce gently until it thickens.",
    "Add two cups of flour and mix well.",
    "Let the dough rest for thirty minutes.",
    "Season with salt and pepper to taste.",
    "Slice the onions thinly and fry them until golden.",
    "Pour the batter into the pan and cook for two minutes on each side.",
    # admin / email
    "Please reply to this email by Friday to confirm your attendance.",
    "Click the link below to verify your email address.",
    "Do not forget to bring a valid photo ID.",
    "Please find the invoice attached.",
    "Contact our support team if you have any questions.",
    "Reset your password by following the steps below.",
    "Please review the attached document and share your feedback.",
    "Forward this message to anyone who might be interested.",
    "Unsubscribe at any time using the link at the bottom of this email.",
    "Keep this receipt for your records.",
    "Need help? Visit our help center.",
    "Have questions? Reach out to our team.",
    "Let us know if you would like to reschedule.",
    # software docs
    "Run pip install requests before importing the module.",
    "Restart the server after changing the configuration file.",
    "Make sure the file exists before opening it.",
    "Use a virtual environment to avoid dependency conflicts.",
    "Do not commit secrets to the repository.",
    "Call close() when you are done with the file handle.",
    "Check the return value for errors.",
    "Import the library at the top of the file.",
    "See the documentation for a full list of options.",
    # travel
    "Arrive at the airport at least two hours before departure.",
    "Keep your passport in a safe place.",
    "Book your tickets early to get the best price.",
    # fitness
    "Warm up for five minutes before you start.",
    "Drink plenty of water during the workout.",
    "Rest for one minute between sets.",
    # tables / reports
    "See the notes below the table for definitions.",
    "Sort the rows by date to compare seasons.",
    "Refer to the appendix for the full list of sources.",
    "Read the footnotes before comparing the figures.",
]

BENIGN_TEST = [
    # gardening
    "Water the plants twice a week and keep them out of direct sunlight.",
    "Trim the hedges in early spring.",
    "Plant the seeds about two centimetres deep.",
    # legal / forms
    "Sign and return the form to the front office.",
    "Please arrive ten minutes before your appointment.",
    "Read the terms and conditions carefully before signing.",
    "Keep the tax documents for at least seven years.",
    # home repair
    "Turn off the main valve before replacing the tap.",
    "Tighten the bolts with a wrench until snug.",
    "Wear protective gloves when handling the chemicals.",
    # IT admin
    "Save your work frequently to avoid losing data.",
    "Update your software to the latest version.",
    "Back up your files before upgrading.",
    "Enable two-factor authentication on your account.",
    "Log in to the portal to view your statement.",
    # finance
    "Submit the expense report by the end of the month.",
    "Compare the quotes before choosing a provider.",
    # cooking
    "Whisk the eggs until fluffy, then fold in the sugar.",
    "Bake for twenty five minutes or until golden brown.",
    "Chill the mixture overnight before serving.",
    # school
    "Bring a laptop and a charger to the workshop.",
    "Remember to submit your homework on time.",
    "Take notes during the lecture and review them weekly.",
    "Please read chapter three before the next class.",
    "Turn the page to continue with the next section.",
    # product labels / services
    "Check the label for allergy information.",
    "Store in a cool dry place away from sunlight.",
    "Shake well before use.",
    "Follow the instructions on the package.",
    "Call us on the number below to book a service.",
    "What are your opening hours? See the schedule below.",
    "Looking for a refund? Follow the steps on our returns page.",
]

PREFIXES = ["", "", "", "Note: ", "Tip: ", "Reminder: ", "Step 2: ", "- "]
