from flask import Flask, request, jsonify
import os
import tempfile
from .core import MoneyThumbSystem


app = Flask(__name__)
money_thumb = MoneyThumbSystem()


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "MoneyThumb"})


@app.route('/process', methods=['POST'])
def process_statement():
    """
    Process bank statement PDF
    
    Expected: multipart/form-data with 'file' field containing PDF
    """
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({"error": "No file provided"}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            temp_path = temp_file.name
        
        try:
            # Process the statement
            result = money_thumb.process_bank_statement(temp_path)
            
            # Generate JSON response
            json_report = money_thumb.generate_json_report(result)
            
            return jsonify(json_report)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/analyze/text', methods=['POST'])
def analyze_text():
    """
    Analyze bank statement from raw text input
    
    Expected: JSON with 'text' field containing statement text
    """
    try:
        data = request.get_json()
        if not data or 'text' not in data:
            return jsonify({"error": "No text provided"}), 400
        
        statement_text = data['text']
        
        # Save text to temporary file for processing
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt') as temp_file:
            temp_file.write(statement_text)
            temp_path = temp_file.name
        
        try:
            # Process the statement
            result = money_thumb.process_bank_statement(temp_path)
            
            # Generate JSON response
            json_report = money_thumb.generate_json_report(result)
            
            return jsonify(json_report)
            
        finally:
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/analyze/mca-positions', methods=['POST'])
def analyze_mca_positions():
    """
    Analyze MCA positions from transaction data
    
    Expected: JSON with transactions array
    """
    try:
        data = request.get_json()
        if not data or 'transactions' not in data:
            return jsonify({"error": "No transactions provided"}), 400
        
        # Convert JSON transactions to Transaction objects
        # This would need proper deserialization in a real implementation
        transactions = data['transactions']
        
        # For now, return a simplified analysis
        mca_count = len([t for t in transactions if 'MCA' in str(t).upper() or 'ADVANCE' in str(t).upper()])
        
        return jsonify({
            "mca_positions_detected": mca_count,
            "analysis": "Simplified MCA detection from transaction data"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500


def run_api():
    """
    Run the MoneyThumb API server
    """
    try:
        # Try localhost first (Windows-friendly)
        app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
    except Exception as e:
        print(f"Failed to start API: {e}")
        print("Starting without debug mode...")
    """
    except OSError as e:
        print(f"Failed to start on 127.0.0.1: {e}")
        print("Trying localhost...")
        try:
            app.run(debug=True, host='localhost', port=5000, threaded=True)
        except OSError as e2:
            print(f"Failed to start on localhost: {e2}")
            print("Starting without debug mode...")
            app.run(debug=False, host='127.0.0.1', port=5000, threaded=True)
    """


if __name__ == '__main__':
    run_api()