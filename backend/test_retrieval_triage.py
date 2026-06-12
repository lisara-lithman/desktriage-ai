import sys
import os
import json
import logging

# Ensure the backend directory is in the import path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging to see retriever messages
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("test_runner")

from app.services import ai_service

def test_triage():
    logger.info("🔄 Loading fine-tuned MLX Model and adapters...")
    ai_service.load_model()
    
    # Check if model loaded successfully
    if ai_service._model is None:
        logger.error("❌ Model failed to load. Cannot run test.")
        return

    # Test Case 1: IT Security policy retrieval test (Password Lockout X-900)
    logger.info("\n=======================================================")
    logger.info("TEST CASE 1: IT Security (Password Expiration - Error X-900)")
    logger.info("=======================================================")
    title_1 = "Workstation shows Error Code X-900"
    desc_1 = "My corporate account seems to be locked and I am getting Error Code X-900 on my laptop screen. How do I reset my password and log back in?"
    
    logger.info(f"Ticket Title: {title_1}")
    logger.info(f"Ticket Description: {desc_1}")
    
    result_1 = ai_service.generate_triage(title_1, desc_1)
    logger.info("Output JSON Result:")
    print(json.dumps(result_1, indent=2))

    # Test Case 2: HR Benefits Guide retrieval test (Portal Session Crash)
    logger.info("\n=======================================================")
    logger.info("TEST CASE 2: HR Benefits (Portal Crash during open enrollment)")
    logger.info("=======================================================")
    title_2 = "HR Portal website freezes when submitting changes"
    desc_2 = "I was trying to update my benefit details on the portal but the browser page froze completely and crashed. Are my changes lost?"
    
    logger.info(f"Ticket Title: {title_2}")
    logger.info(f"Ticket Description: {desc_2}")
    
    result_2 = ai_service.generate_triage(title_2, desc_2)
    logger.info("Output JSON Result:")
    print(json.dumps(result_2, indent=2))

    # Test Case 3: Facilities Ops retrieval test (Office Printer Jam)
    logger.info("\n=======================================================")
    logger.info("TEST CASE 3: Facilities Operations (Printer paper jam)")
    logger.info("=======================================================")
    title_3 = "The second floor office printer is jammed"
    desc_3 = "I tried to print my documents and the printer on the second floor jammed. There is paper stuck in the fuser unit."
    
    logger.info(f"Ticket Title: {title_3}")
    logger.info(f"Ticket Description: {desc_3}")
    
    result_3 = ai_service.generate_triage(title_3, desc_3)
    logger.info("Output JSON Result:")
    print(json.dumps(result_3, indent=2))

    # Test Case 4: IT Security (VPN Connection Failure - Error X-404)
    logger.info("\n=======================================================")
    logger.info("TEST CASE 4: IT Security (VPN connection error X-404)")
    logger.info("=======================================================")
    title_4 = "Error Code X-404 on VPN client"
    desc_4 = "I am trying to connect to the corporate network from home using Cisco AnyConnect. It keeps timing out and giving me terminal Error Code X-404. I've restarted my laptop but still can't get in. What are the steps to fix this routing error?"
    
    logger.info(f"Ticket Title: {title_4}")
    logger.info(f"Ticket Description: {desc_4}")
    
    result_4 = ai_service.generate_triage(title_4, desc_4)
    logger.info("Output JSON Result:")
    print(json.dumps(result_4, indent=2))


if __name__ == "__main__":
    test_triage()
