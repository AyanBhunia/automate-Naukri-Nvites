import time
import random
from playwright.sync_api import sync_playwright

# --- Configuration ---
# Use a local directory for user data to persist sessions (cookies, local storage)
USER_DATA_DIR = "./user_data" 
NVITES_URL = "https://www.naukri.com/mnjuser/inbox"
HEADLESS = False

# Cognitive Engine Knowledge Base
USER_KNOWLEDGE_BASE = {
    'notice_period': '15 Days',
    'notice period': '15 Days',
    'ctc': '12 LPA',
    'current ctc': '12 LPA',
    'expected ctc': '15 LPA',
    'relocation': 'Yes',
    'relocate': 'Yes',
    'experience': '5 Years',
    'total experience': '5 Years'
}

def random_sleep(min_seconds=2, max_seconds=5):
    time.sleep(random.uniform(min_seconds, max_seconds))

def login_check(page):
    """
    Checks if the user is logged in. If not, pauses for manual login.
    """
    print(f"Navigating to {NVITES_URL}...")
    page.goto(NVITES_URL)
    
    # Check if redirected to login page or if generic login elements exist
    if "login" in page.url or page.locator("input[type='password']").count() > 0:
        print("\n" + "="*50)
        print("LOGIN REQUIRED")
        print("Please log in manually in the browser window.")
        print("Solve any CAPTCHAs if presented.")
        print("Navigate back to https://www.naukri.com/mnjuser/inbox if not redirected automatically.")
        input("Press Enter here once you are logged in and looking at the NVites page...")
        print("="*50 + "\n")
    else:
        print("Session appears valid. Proceeding...")

def wait_for_shimmers(page):
    """
    Waits for loading shimmers to disappear and cards to appear.
    """
    print("Waiting for content to load...")
    try:
        # Wait for shimmer to disappear
        page.wait_for_selector(".inbox-card-shimmer", state="hidden", timeout=10000)
        # Wait for at least one card to be visible
        page.wait_for_selector(".inbox-card, .cards", state="visible", timeout=10000)
        print("Content loaded.")
    except Exception as e:
        print(f"Warning: Content wait timed out: {e}. Attempting to refresh if needed.")
        if NVITES_URL not in page.url:
            page.goto(NVITES_URL)
            page.wait_for_load_state("networkidle")

def get_valid_cards(page):
    """
    Selects job cards and filters out Ads/Sponsored content.
    """
    print("Scanning for job cards...")
    # The prompt mentions .cards container. 
    # If the structure is complex, we might need to be more generic. 
    # Assuming .cards contains the list items.
    
    # Try multiple common container selectors
    container_selectors = [".cards", ".inbox-container", ".list-container"]
    container = None
    for sel in container_selectors:
        if page.locator(sel).count() > 0:
            container = page.locator(sel)
            break
            
    if not container:
        print("Could not find job container. Using generic body search...")
        cards_locator = page.locator(".inbox-company-card")
    else:
        # Valid jobs have the class 'inbox-company-card'
        cards_locator = container.locator(".inbox-company-card")
    
    card_count = cards_locator.count()
    print(f"Found {card_count} total potential elements. Filtering...")

    valid_card_indices = []
    for i in range(card_count):
        try:
            card = cards_locator.nth(i)
            if not card.is_visible():
                continue
            
            # Use specific selectors from the HTML dump
            title_el = card.locator(".title")
            company_el = card.locator(".comp-name")
            
            if title_el.count() == 0:
                continue
                
            text_content = card.inner_text()
            text_content_lower = text_content.lower()
            
            # Filter out promotional content
            skip_keywords = ["become a pro", "premium", "sponsored", "naukri pro", "upgrade your profile"]
            if any(kw in text_content_lower for kw in skip_keywords):
                continue
            
            # Filter out ALREADY APPLIED jobs
            if "applied" in text_content_lower:
                # Double check specific tag if needed, but text check is safer
                # HTML dump showed: <span class="apply tag">Applied</span>
                print(f"Skipping Card {i}: Already Applied.")
                continue

            # DEBUG: Print structure of potential valid card


            valid_card_indices.append(i)
        except Exception as e:
            continue

    print(f"Identified {len(valid_card_indices)} valid job cards.")
    return valid_card_indices, cards_locator

    print(f"Identified {len(valid_card_indices)} valid job cards.")
    return valid_card_indices, cards_locator

def handle_modal(page):
    """
    Handles the sequential Q&A form. 
    Loops through questions, answering them from the KB or prompting the user.
    """
    print("Starting Q&A handler...")
    
    # Loop for multiple steps/questions
    max_steps = 10
    for step in range(max_steps):
        # Wait a bit for the form to settle/animation
        page.wait_for_timeout(1500)
        
        # Check if we are done (no more Save/Next buttons, or Success message)
        # Assuming "Save" or "Next" button implies a question is active.
        save_btn = page.locator("button:has-text('Save'), button:has-text('Next'), button:has-text('Submit')").first
        
        if not save_btn.is_visible():
            print("No 'Save/Next' button visible. Checking for completion...")
            # Check for success message or closed drawer
            if page.locator(".success-message, .applied-success").is_visible() or not page.locator(".drawer-content").is_visible():
                print("Application appears complete.")
                break
            # If not complete but no button, maybe it's loading?
            page.wait_for_timeout(2000)
            if not save_btn.is_visible():
                print("Still no button. Assuming end of form.")
                break

        print(f"--- Form Step {step + 1} ---")
        
        # Identify the Question Label
        # Looking for visible labels in the active form container
        labels = page.locator("label").all()
        # Filter for visible labels only
        visible_labels = [l for l in labels if l.is_visible()]
        
        if not visible_labels:
            print("No visible question labels found. Clicking Save/Submit anyway...")
            save_btn.click()
            continue

        # Process the first visible label (usually the current question)
        label = visible_labels[0]
        question_text = label.inner_text().lower().strip()
        print(f"Question: '{question_text}'")

        # Determine Answer
        answer = None
        # Fuzzy match
        for key, val in USER_KNOWLEDGE_BASE.items():
            if key in question_text:
                answer = val
                break
        
        # If no answer in KB, ASK THE USER
        if not answer:
            print(f"!!! UNKNOWN QUESTION: '{question_text}' !!!")
            print("Please type the answer below (or 'skip' to ignore, 'manual' to do it yourself in browser):")
            user_input = input("Answer > ").strip()
            
            if user_input.lower() == 'manual':
                input("Perform manual action in browser and press Enter here to continue...")
                continue
            elif user_input.lower() != 'skip':
                answer = user_input
                # Save to KB for this session (could verify with user if they want to save permanently)
                USER_KNOWLEDGE_BASE[question_text] = answer
                print(f"Saved '{question_text}': '{answer}' to session knowledge base.")

        if answer:
            print(f"Answering: '{answer}'")
            # Try to fill the input
            # 1. Check for ID in 'for' attribute
            for_id = label.get_attribute("for")
            input_el = None
            if for_id:
                input_el = page.locator(f"#{for_id}")
            
            # 2. If no ID, try looking inside the label's parent or nearby
            if not input_el or input_el.count() == 0:
                 # heuristic: input is usually a sibling or child
                 input_el = label.locator("xpath=..//input | ..//textarea | ..//select").first
            
            if input_el and input_el.count() > 0:
                try:
                    tag = input_el.evaluate("el => el.tagName").lower()
                    inputType = input_el.get_attribute("type")
                    
                    if tag == "select":
                        input_el.select_option(label=answer)
                    elif inputType in ["radio", "checkbox"]:
                         # For radio/checkbox, we might need to click the one with the value 'answer'
                         # or click the label containing 'answer'
                         option_label = page.locator(f"label:has-text('{answer}')").first
                         if option_label.is_visible():
                             option_label.click()
                         else:
                             input_el.check()
                    else:
                        input_el.fill(answer)
                except Exception as e:
                    print(f"Error filling input: {e}")
            else:
                print("Could not locate input field for this label.")

        # Click Save/Next
        print("Clicking Save/Next...")
        save_btn.click()
        
    print("Q&A sequence finished.")

def process_job_application(context, page, card, index):
    """
    Handles the click, tab switch, and apply logic for a single card.
    """
    print(f"\nProcessing Job #{index + 1}...")
    
    # 0. Check for and close Chatbot Overlay
    try:
        chatbot_close = page.locator(".chatbot_Overlay .cross-icon, .chatbot_Overlay .close, #_rkujmy8yj2").first
        if chatbot_close.is_visible():
            print("Chatbot overlay detected. Closing...")
            # Try clicking the overlay itself or a close button
            # Sometimes clicking the overlay background closes it
            page.mouse.click(10, 10) # Click somewhere safe?
            # Or try executing js to remove it
            page.evaluate("document.querySelectorAll('.chatbot_Overlay').forEach(e => e.remove())")
    except:
        pass

    # Scroll into view
    card.scroll_into_view_if_needed()
    
    # Click Strategy: Coordinate-based click on Title or Card
    try:
        # Target the title first
        target = card.locator(".title").first
        if not target.is_visible():
            target = card.first # Fallback to whole card

        # Get bounding box
        box = target.bounding_box()
        if box:
            print(f"Clicking at coordinates: x={box['x'] + box['width']/2}, y={box['y'] + box['height']/2}")
            
            # Hover first
            page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
            page.wait_for_timeout(500)
            
            # Click
            page.mouse.down()
            page.wait_for_timeout(100)
            page.mouse.up()
            
            # Wait for reaction
            try:
                # Look for JD container or Apply button
                page.wait_for_selector(".job-description-container, .right-pane, button:has-text('Apply')", timeout=5000)
                print("UI reacted to click.")
            except:
                print("No immediate UI reaction. Trying double click...")
                page.mouse.dblclick(box['x'] + box['width']/2, box['y'] + box['height']/2)
                page.wait_for_timeout(3000)
        else:
            print("Could not get bounding box for target.")

    except Exception as e:
        print(f"Mouse interaction failed: {e}")
        
    try:
        # Check for Apply Button

        
        try:
            # Wait a bit for any reaction
            page.wait_for_timeout(2000)
            
            # Check for Apply Button
            # Using a very broad selector to catch any apply button
            apply_btn = page.locator("button, a").filter(has_text="Apply").first
            
            if apply_btn.is_visible():
                btn_text = apply_btn.inner_text().lower()
                print(f"Apply button found: '{btn_text}'")
                
                if "company website" in btn_text:
                    print("External application detected. Skipping.")
                else:
                    print("Clicking Apply...")
                    apply_btn.click()
                    
                    # Simplified Handling: Just check for success or skip form
                    try:
                        # Wait briefly to see result
                        page.wait_for_timeout(2000)
                        
                        # Check for Success Message
                        # Use a list of locators or OR logic correctly
                        success_msg = page.locator(".success-message, .applied-success").or_(page.locator("text=successfully applied")).first
                        if success_msg.is_visible():
                            print("SUCCESS: Application Submitted!")
                        else:
                            # Check if a form opened (drawer/modal)
                            drawer = page.locator(".drawer-content, .modal").first
                            if drawer.is_visible():
                                print("Form detected. SKIPPING form filling as requested.")
                                # Optional: Click 'Save' once just in case it's a simple confirm? 
                                # No, user said skip form.
                            else:
                                print("No immediate success message or form. Moving on...")
                                
                    except Exception as e:
                        print(f"Error checking post-apply state: {e}")

            else:
                print("Apply button not visible. Dumping page text snippet to debug...")
                # Debug: print some text from the page to see where we are
                print(page.locator("body").inner_text()[:500])

        except Exception as e:
            print(f"Error finding apply button: {e}")

    except Exception as e:
        print(f"Error interacting with card: {e}")

    # Cleanup: If there's a back button or close button for the pane, click it.
    # If it's split view, we might not need to do anything, just click the next card.
    # But to be safe, we can try to find a 'close' button.
    close_btn = page.locator(".close-icon, .cross-icon, [aria-label='Close']").first
    if close_btn.is_visible():
        print("Closing detail view...")
        close_btn.click()
    else:
        # If no close button, maybe we are just on the list.
        pass
        
    # Ensure we are back at the list
    if not page.locator(".inbox-company-card").first.is_visible():
        print("List not visible. Navigating to inbox...")
        page.goto(NVITES_URL)
        wait_for_shimmers(page)

def main():
    print("Initializing Playwright with persistent context...")
    with sync_playwright() as p:
        # Persistent context to save login state
        context = p.chromium.launch_persistent_context(
            user_data_dir=USER_DATA_DIR,
            headless=HEADLESS,
            args=["--start-maximized"],
            no_viewport=True
        )
        
        page = context.pages[0]
        
        try:
            # 1. Login Check & Navigation
            login_check(page)
            
            # 2. Shimmer Wait
            wait_for_shimmers(page)
            
            # 4. Loop first 5
            max_process = 5
            print(f"Processing up to {max_process} cards...")
            
            attempted_identifiers = set()
            processed_count = 0
            
            while processed_count < max_process:
                # Re-fetch cards every time because the page might have reloaded
                indices, cards_locator = get_valid_cards(page)
                
                if not indices:
                    print("No valid cards found.")
                    break
                
                target_index = None
                target_card = None
                
                # Find the first valid card that hasn't been attempted
                for idx in indices:
                    try:
                        card = cards_locator.nth(idx)
                        # Extract identifier to track duplicates/already processed
                        # Use first() to be safe, though get_valid_cards checks existence
                        title = card.locator(".title").first.inner_text().strip()
                        company = card.locator(".comp-name").first.inner_text().strip()
                        identifier = f"{title}|{company}"
                        
                        if identifier not in attempted_identifiers:
                            target_index = idx
                            target_card = card
                            attempted_identifiers.add(identifier)
                            break
                    except Exception as e:
                        print(f"Skipping index {idx} due to error reading details: {e}")
                        continue
                
                if target_index is None:
                    print("All currently valid cards have been attempted in this session.")
                    break
                
                # Process the found card
                process_job_application(context, page, target_card, processed_count)
                processed_count += 1
                random_sleep()
                
            print("\nAutomation sequence complete.")
            print("="*50)
            print("The browser will remain open so you can handle any forms manually.")
            print("Press Ctrl+C in this terminal when you are ready to close the browser.")
            print("="*50)
            
            # Keep script alive
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nUser stopped the script.")
            
        except Exception as e:
            print(f"Critical Error: {e}")
            # Even on error, keep browser open for inspection
            try:
                input("Error occurred. Press Enter to close browser...")
            except:
                pass
        finally:
            print("Closing browser...")
            try:
                context.close()
            except Exception:
                # Ignore errors if browser is already closed
                pass

if __name__ == "__main__":
    main()
