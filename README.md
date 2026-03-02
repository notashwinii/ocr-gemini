## How to Run

1. **Clone and enter the project**
	```bash
	git clone <repo-url>
	cd ocr-gemini
	```

2. **Create a virtual environment**
	- Windows:
	  ```powershell
	  python -m venv venv
	  .\venv\Scripts\activate
	  ```
	- Linux / macOS:
	  ```bash
	  python3 -m venv venv
	  source venv/bin/activate
	  ```

3. **Install dependencies**
	```bash
	pip install -r requirements.txt
	```

4. **Configure environment variables**
	```bash
	cp env.example .env
	# update the values in .env
	```

5. **Run the app**
	```bash
	python main.py
	```

	Access the FastAPI server at http://localhost:8000.
