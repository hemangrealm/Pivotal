# 
Unlock your financial freedom with Percentile Pocket! A powerful interactive simulation tool that runs 10,000 Monte Carlo projections to analyze risk and project wealth. Customize financial parameters instantly through a command-line interface and explore detailed browser reports to optimize your future trajectory.Features an interactive CLI setup and automatically generates publication-ready browser analytics dashboards.
 It calculates potential portfolio paths, tests sequence-of-returns risk, and generates intuitive HTML reports directly in your browser.

 ## ✨ Features

- *Interactive CLI Setup:* Quick prompt-driven inputs for assets, income, inflation, and withdrawal strategies.
- *Monte Carlo Engine:* Performs 10,000 statistical market path simulations for precise probability distributions.
- *Automated Reporting:* Generates an interactive visual output (my-output/report.html) automatically upon execution.
- *Customizable Profiles:* Save and reload custom financial parameters seamlessly.

---

## 🛠️ Quick Start

### Prerequisites
- Python 3.14 installed on your system.

### Running the Interactive Simulation

1. *Clone the Repository:*
   ```bash
   git clone [https://github.com/hemangrealm/percentile-pocket.git](https://github.com/hemangrealm/percentile-pocket.git)
   cd percentile-pocket

2. Set Up Virtual Environment
   # Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate

4. Install Dependencies 
pip install -r requirements.txt

5. Quick Start (Windows Launcher)
If you are running the project on Windows, execute the included batch script to automatically load dependencies and trigger the simulator:
run_simulation.bat

# 📂 Project Structure
Plaintext
Percentile-Pocket/
│
├── my-output/             # Generated output reports (HTML dashboards)
├── venv/                  # Virtual environment (ignored by Git)
├── ant.py                 # Core Monte Carlo simulation engine
├── run_simulation.bat     # Windows automated execution script
├── requirements.txt       # Project dependencies
├── .gitignore             # Git exclusion rules
├── LICENSE                # MIT License terms
└── README.md              # Project 
