from flask import Flask, request, jsonify, abort
from flask_cors import CORS  # Import Flask-CORS for CORS support
from rapidfuzz.distance import JaroWinkler
from metaphone import doublemetaphone
import psutil  # For system health monitoring
import time
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
from unidecode import unidecode
import socket
import uuid
from functools import wraps
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from difflib import SequenceMatcher

# Configure logging with log rotation
handler = RotatingFileHandler('error.log', maxBytes=1024 * 1024 * 5, backupCount=3)  # 5MB per file, 3 backups
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger("app_logger")
logger.addHandler(handler)
logger.setLevel(logging.INFO)

app = Flask(__name__)

# Enable CORS for the Flask app
CORS(app, resources={r"/api/*": {"origins": "*"}})  # Allow all origins for API endpoints

# Configure request payload size limit
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024  # Limit payload size to 2MB

# API Version prefix
API_VERSION = '/api/v1'

# API Key for authentication
API_KEY = "your-secure-api-key"

# Configure rate limiting
limiter = Limiter(
    get_remote_address,  # Function to determine the key
    app=app  # Associate with the Flask app
)

def require_api_key(f):
    """Decorator to enforce API key authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.headers.get("x-api-key") != API_KEY:
            abort(403, description="Forbidden: Invalid API key.")
        return f(*args, **kwargs)
    return decorated_function

# Standardized Response Wrapper
def create_response(data=None, message="Success", status=200, error_code=None):
    """
    Standardize the API response format.

    Args:
        data (dict): The data payload to include in the response.
        message (str): A human-readable message describing the response.
        status (int): The HTTP status code for the response.
        error_code (str): An optional error code for troubleshooting.

    Returns:
        tuple: A tuple containing the JSON response and the HTTP status code.
    """
    response_id = str(uuid.uuid4())  # Generate a unique response ID
    response = {
        "status": "success" if status == 200 else "error",
        "message": message,
        "data": data,
        "response_id": response_id  # Add the response ID
    }

    # Include an error code if provided (useful for troubleshooting)
    if error_code:
        response["error_code"] = error_code

    # Log the response details for traceability
    logger.info(f"Response ID: {response_id}, Status: {status}, Message: {message}, Error Code: {error_code}")

    return jsonify(response), status


# Health Check Endpoint
@app.route(f'{API_VERSION}/health', methods=['GET'])
def health_check():
    """Endpoint to check system health."""
    try:
        # System metrics
        cpu_usage = psutil.cpu_percent()
        memory_info = psutil.virtual_memory()
        disk_info = psutil.disk_usage('/')
        hostname = socket.gethostname()
        ip_address = socket.gethostbyname(hostname)
        load_avg = os.getloadavg()

        health_status = {
            "status": "healthy",
            "cpu_usage": f"{cpu_usage}%",
            "memory": {
                "total": memory_info.total,
                "available": memory_info.available,
                "used": memory_info.used,
                "percent": memory_info.percent
            },
            "disk": {
                "total": disk_info.total,
                "used": disk_info.used,
                "free": disk_info.free,
                "percent": disk_info.percent
            },
            "load_average": {
                "1_min": load_avg[0],
                "5_min": load_avg[1],
                "15_min": load_avg[2]
            },
            "hostname": hostname,
            "ip_address": ip_address,
            "timestamp": datetime.now().isoformat()
        }

        return jsonify(health_status), 200

    except OSError as e:
        logger.error(f"[health_check] OSError occurred: {e}", exc_info=True)
        return jsonify({"message": "Internal Server Error: Unable to retrieve system metrics."}), 500
    except Exception as e:
        logger.error(f"[health_check] Error occurred: {e}", exc_info=True)
        return jsonify({"message": "Internal Server Error"}), 500


# Helper functions
def validate_name(name):
    """Synchronous validation of a name."""
    if not name or not name.strip():
        return "Name cannot be empty."

    if len(name) > 100:
        return "Name exceeds the maximum length of 100 characters."

    if not name.replace(' ', '').isalnum():
        return "Name contains invalid characters. Only alphanumeric and space characters are allowed."

    return None

def enhanced_name_match(name1, name2, debug=False):
    from difflib import SequenceMatcher

# Mocking Jaro-Winkler similarity using SequenceMatcher
class JaroWinkler:
    @staticmethod
    def similarity(a, b):
        return SequenceMatcher(None, a, b).ratio()

# Updated function with reversed names, initials boost, and dynamic weights
def enhanced_name_match(name1, name2, debug=False):
    """Improved name matching with handling of reversed names and initials."""
    # Normalize names
    name1 = name1.lower()
    name2 = name2.lower()

    # Tokenize names
    tokens1 = name1.split()
    tokens2 = name2.split()

    # Adjust weights: First token (0.5), second token (0.3), remaining tokens (0.2)
    # The first token often represents a critical part of a name (e.g., surname or first name),
    # so it is given the highest weight. The second token is slightly less important,
    # while the remaining tokens receive smaller weights to balance their contribution.
    
    num_tokens1 = len(tokens1)
    num_tokens2 = len(tokens2)
    
    if max(num_tokens1, num_tokens2) == 2:
        weights = [0.6, 0.4]  # Two-word names: Higher priority to first token
    elif max(num_tokens1, num_tokens2) == 3:
        weights = [0.4, 0.3, 0.3]  # Three-word names: Balanced priority
    elif max(num_tokens1, num_tokens2) >= 4:
        weights = [0.3, 0.3, 0.2, 0.2]  # Four or more words: Evenly distributed
    else:
        weights = [0.5] * max(num_tokens1, num_tokens2)  # Fallback for unexpected cases

    max_len = max(len(tokens1), len(tokens2))
    adjusted_weights = [weights[i] if i < len(weights) else 0.1 for i in range(max_len)]

    if debug:
        print(f"Step 1: Adjusted Weights: {adjusted_weights}")


    # Check for reversed tokens and add a boost
    # This check identifies if the tokens in the two names are in reverse order.
    # For example, 'First Last' vs 'Last First'. If a reversal is detected, a slight bonus (+0.1)
    # is added to the final score to account for this pattern.
    reversed_bonus = 0.0
    if tokens1 == tokens2[::-1]:
        reversed_bonus = 0.1  # Bonus for reversed names
        if debug:
            print(f"Step 2: Reversed names detected! Tokens: {tokens1} -> {tokens2[::-1]}")
            print("Step 2: Adding reversed name bonus: +0.1")

    scores = []

    # Best Token Pairing Matching with Boost for Initials
    print("Step 3: Token Matching")
    for i, token1 in enumerate(tokens1):
        best_score = 0
        for token2 in tokens2:
            score = JaroWinkler.similarity(token1, token2)
            # Boost score for initials matching
            # Initials are often used as abbreviations for longer names (e.g., 'J' for 'John').
            # If a token consists of a single character and matches the start of another token,
            # it receives a boosted score (up to 0.9) to reflect its intended importance.
            if len(token1) == 1 and token2.startswith(token1):
                score = max(score, 0.9)
            best_score = max(best_score, score)
        weight = adjusted_weights[i]
        scores.append(best_score * weight)
        if debug:
            print(f"    Token '{token1}' Best Match: {best_score:.2f}, Weight: {weight:.2f}, Weighted Score: {best_score * weight:.2f}")

    # Token Overlap
    set_tokens1 = set(tokens1)
    set_tokens2 = set(tokens2)
    intersection = set_tokens1.intersection(set_tokens2)
    union = set_tokens1.union(set_tokens2)
    token_overlap = len(intersection) / len(union) if union else 0

    if debug:
        print(f"Step 4: Token Overlap = {token_overlap:.2f} (Intersection: {intersection}, Union: {union})")

    # Fuzzy Similarity
    fuzzy_scores = []
    print("Step 5: Fuzzy Similarity Calculation")
    for token1 in set_tokens1:
        best_score = max(JaroWinkler.similarity(token1, token2) for token2 in set_tokens2)
        fuzzy_scores.append(best_score)
        if debug:
            print(f"    Token '{token1}' Best Match Score: {best_score:.2f}")
    fuzzy_similarity = sum(fuzzy_scores) / len(fuzzy_scores) if fuzzy_scores else 0

    if debug:
        print(f"Step 6: Fuzzy Similarity = {fuzzy_similarity:.2f}")

    # Final Weighted Scoring
    sum_scores = sum(scores)
    # The final score is a weighted combination of:
    # - sum_scores: the weighted sum of best token matches (40% importance)
    # - token_overlap: the fraction of overlapping tokens (30% importance)
    # - fuzzy_similarity: the average similarity between tokens (30% importance)
    # The reversed_bonus is added as a slight adjustment (+0.1) to account for reversed first and last names.

    #modified the logic of percentage correction
    final_score = min((0.4 * sum_scores + 0.3 * token_overlap + 0.3 * fuzzy_similarity + reversed_bonus),1.0)*100


    if debug:
        print(f"Step 7: Final Score Calculation")
        print(f"    Sum of Weighted Scores: {sum_scores:.2f}")
        print(f"    Token Overlap: {token_overlap:.2f}")
        print(f"    Fuzzy Similarity: {fuzzy_similarity:.2f}")
        print(f"    Reversed Bonus: {reversed_bonus:.2f}")
        print(f"    Final Weighted Score: {final_score:.2f}")

    return {
        "Fuzzy Similarity": round(fuzzy_similarity, 2),
        "Token Overlap": round(token_overlap, 2),
        "Final Weighted Score": round(final_score, 2),
        "Match": final_score > 0.7
    }

# Test matching "Mevada Kirtikumar Jagjivandas" and "KIRTIKUMAR J MEVADA"
#name1 = "Mevada Kirtikumar Jagjivandas"
#name2 = "KIRTIKUMAR J MEVADA"
#added input for user defined values
name1 =input("enter the name1: ")
name2 =input("enter the name2: ")

print(f"--- Matching '{name1}' vs '{name2}' (Updated Function with Debug) ---")

#changed the function name
updated_result = enhanced_name_match(name1, name2, debug=True)
updated_result



@app.route(f'{API_VERSION}/batch_match', methods=['POST'])
@require_api_key
@limiter.limit("5 per minute")  # Limit to 5 batch requests per minute per user
def batch_match_names():
    """Batch processing for name matching with optimized performance."""
    try:
        # Ensure Content-Type is JSON
        if not request.is_json:
            abort(400, description="Request body must be JSON.")

        # Ensure the JSON body is well-formed
        try:
            data = request.get_json()
        except Exception:
            abort(400, description="Malformed JSON. Please check your request body.")

        pairs = data.get("pairs", [])

        # Validate input
        if not isinstance(pairs, list):
            abort(400, description="Invalid input: 'pairs' must be a list of name pairs.")

        if len(pairs) > 500:
            abort(400, description="Batch size exceeds the limit of 500 name pairs.")

        for pair in pairs:
            if not isinstance(pair, dict):
                abort(400, description="Each pair must be a dictionary containing 'name1' and 'name2'.")

            if "name1" not in pair or "name2" not in pair:
                abort(400, description="Each pair must include 'name1' and 'name2'.")

        # Separate valid and invalid pairs
        invalid_pairs = []
        valid_pairs = []

        for pair in pairs:
            name1 = pair.get("name1")
            name2 = pair.get("name2")
            error1 = validate_name(name1)
            error2 = validate_name(name2)

            if error1 or error2:
                invalid_pairs.append({"name1": name1, "name2": name2, "error": error1 or error2})
            else:
                valid_pairs.append((name1, name2))

        # Pagination
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        start = (page - 1) * page_size
        end = start + page_size

        # Process valid pairs
        results = [enhanced_name_match(pair[0], pair[1]) for pair in valid_pairs[start:end]]

        # Prepare response data
        response_data = {
            "valid_results": results,
            "invalid_pairs": invalid_pairs,
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_valid_pairs": len(valid_pairs),
                "total_invalid_pairs": len(invalid_pairs),
                "next_page": page + 1 if end < len(valid_pairs) else None,
                "previous_page": page - 1 if page > 1 else None
            }
        }

        return create_response(data=response_data)
    except Exception as e:
        logger.exception("Unexpected error during batch name matching.")
        return create_response(message="An error occurred during batch processing.", status=500)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
