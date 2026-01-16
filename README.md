# Format Converter

A powerful web application that converts between JSON, TOON, CSV, and YAML formats. Built with React for the frontend and Python Flask for the backend.

## Features

- **Multi-format conversion**: Convert between JSON, TOON, CSV, and YAML
- **Bidirectional conversion**: Paste content in any format and get all other formats
- **Auto-conversion**: Real-time conversion as you type (with debouncing)
- **Token counting**: See token counts for each format using tiktoken (GPT-4 compatible)
- **LLM recommendations**: Get recommendations for the most token-efficient format
- **Copy & Download**: Easy copy and download for each format
- **Modern, responsive UI**: Clean 4-box parallel layout (TOON, JSON, YAML, CSV)

## Project Structure

```
tokenfusion/
├── backend/
│   ├── app.py              # Flask backend server
│   ├── converter.py        # JSON to TOON conversion logic (legacy)
│   ├── multi_converter.py  # Multi-format converter (JSON, TOON, CSV, YAML)
│   ├── token_counter.py     # Token counting utilities using tiktoken
│   ├── test_converter.py   # Unit tests for converter
│   ├── test_api.py         # API endpoint tests
│   ├── pytest.ini          # Pytest configuration
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.js          # Main React component
│   │   ├── App.css         # Styles
│   │   ├── index.js        # React entry point
│   │   └── index.css       # Global styles
│   └── package.json        # Node dependencies
└── README.md
```

## Setup Instructions

### Backend Setup

1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   ```

3. Activate the virtual environment:
   - On Windows:
     ```bash
     venv\Scripts\activate
     ```
   - On macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

5. Run the Flask server:
   ```bash
   python app.py
   ```

   The backend will run on `http://localhost:5000`

### Frontend Setup

1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the React development server:
   ```bash
   npm start
   ```

   The frontend will run on `http://localhost:3000` and automatically open in your browser.

## Usage

1. Make sure both the backend and frontend servers are running
2. Open your browser to `http://localhost:3000`
3. Paste content into any of the 4 format boxes (TOON, JSON, YAML, or CSV - in that order)
4. The content will automatically convert to all other formats
5. View token counts at the bottom of each box
6. See the recommendation for the most token-efficient format below the boxes
7. Use the copy (📋) or download (📥) buttons for any format

### Example Workflow:
- Paste JSON into the JSON box → Get TOON, CSV, and YAML automatically
- See token counts for each format displayed at the bottom of each box
- Get a recommendation showing which format uses the least tokens for LLM usage
- Paste CSV into the CSV box → Get JSON, TOON, and YAML automatically
- Paste TOON into the TOON box → Get JSON, CSV, and YAML automatically
- Paste YAML into the YAML box → Get JSON, TOON, and CSV automatically

### Token Counting:
- Token counts are calculated using `tiktoken` with GPT-4 encoding
- The format with the lowest token count is highlighted and recommended
- This helps optimize data for LLM API usage and reduce costs

## API Endpoints

- `POST /api/convert` - Converts content from one format to all other formats
  - Request body: `{ "content": "...", "from_format": "json|toon|csv|yaml" }`
  - Returns: `{ "success": true, "json": "...", "toon": "...", "csv": "...", "yaml": "..." }`
  
- `GET /api/health` - Health check endpoint

## Supported Formats

### JSON
Standard JSON format with nested objects and arrays.

### TOON
TOON (Text Object Oriented Notation) is a compact, token-efficient format with minimal whitespace. Uses dot notation for nesting and bracket notation for arrays.

Example:
```
name:John
age:30
address.city:New York
address.zip:10001
hobbies[0]:reading
hobbies[1]:coding
```

**Key Features:**
- No indentation (minimal whitespace)
- Dot notation for nested objects (`parent.child:value`)
- Bracket notation for arrays (`items[0]:value`)
- Designed to minimize tokens for LLM usage

### CSV
Comma-separated values format. Objects are converted to rows with headers.

### YAML
YAML (YAML Ain't Markup Language) format, human-readable data serialization.

## Testing

The project includes extensive test coverage for the JSON to TOON conversion functionality.

### Running Tests

1. Make sure you're in the backend directory and have installed dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. Run all tests:
   ```bash
   pytest
   ```

3. Run tests with coverage report:
   ```bash
   pytest --cov=converter --cov=app --cov-report=html
   ```
   This will generate an HTML coverage report in `htmlcov/index.html`

4. Run specific test files:
   ```bash
   pytest test_converter.py -v
   pytest test_api.py -v
   ```

5. Run a specific test class or test:
   ```bash
   pytest test_converter.py::TestBasicTypes -v
   pytest test_converter.py::TestBasicTypes::test_string_value -v
   ```

### Test Coverage

The test suite includes:

- **Basic Types**: Strings, integers, floats, booleans, null values
- **Simple Objects**: Single and multiple key-value pairs
- **Nested Objects**: One to multiple levels of nesting
- **Arrays**: Empty, simple, mixed types, nested arrays
- **Complex Structures**: Real-world JSON examples
- **Edge Cases**: Special characters, empty objects, large numbers, etc.
- **Root Level Types**: Arrays, primitives as root elements
- **Indentation**: Correctness of indentation at all levels
- **API Endpoints**: File upload, JSON body, error handling

## Technologies Used

- **Frontend**: React 18, Axios
- **Backend**: Python 3, Flask, Flask-CORS
- **Libraries**: 
  - PyYAML (for YAML support)
  - tiktoken (for LLM token counting)
- **Testing**: pytest, pytest-cov
- **Styling**: CSS3 with modern design
