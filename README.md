# Green Time Schedule API

An API for scheduling batch jobs during periods of lowest CO2 intensity on the electrical grid. This service helps reduce the carbon footprint of your computing workloads by scheduling them when the electrical grid is using more renewable energy.

## Features

- **CO2-Aware Scheduling**: Find optimal time slots with the lowest carbon intensity
- **Flexible Scheduling**: Support for jobs from 30 minutes to 24 hours
- **Smart Caching**: Efficient caching of carbon intensity forecasts
- **Alternative Options**: Returns backup time slots if primary isn't suitable
- **UK Grid Focus**: Integrated with the UK Carbon Intensity API

## Installation

### Prerequisites

- Python 3.9+
- UV package manager (for dependency management and virtual environments)

### Setup

1. Clone the repository:

```bash
git clone https://github.com/yourusername/greentimeschedule.git
cd greentimeschedule
```

2. Create and activate a virtual environment:

```bash
# Using UV
uv venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:

```bash
# Install using UV from pyproject.toml and uv.lock
uv sync
```


## Usage

### Starting the API server

```bash
fastapi dev ./app/main.py
```

The API will be available at http://localhost:8000.

API documentation is available at:
- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

### Example API Requests

#### Schedule a job

```bash
curl -X POST "http://localhost:8000/api/v1/schedule/job" \
  -H "Content-Type: application/json" \
  -d '{
    "job_duration_minutes": 120,
    "deadline_utc": "2024-06-20T18:00:00Z",
    "job_name": "data-processing-batch",
    "priority": "low"
  }'
```

#### Get carbon intensity forecast

```bash
curl -X GET "http://localhost:8000/api/v1/carbon/forecast/2024-06-20"
```

## API Endpoints

### Scheduling

- `POST /api/v1/schedule/job` - Schedule a job for the optimal time slot

### Carbon Intensity

- `GET /api/v1/carbon/forecast/{date}` - Get carbon intensity forecast for a specific date
- `GET /api/v1/carbon/forecast?start_date={date}&end_date={date}` - Get carbon intensity forecast for a date range

### System

- `GET /health` - Health check endpoint
- `GET /` - Root endpoint (redirects to docs)

## Configuration

The API can be configured using environment variables:

- `DEBUG` - Enable debug mode (default: False)
- `REDIS_URL` - Redis URL for caching (default: None, uses in-memory cache)
- `CARBON_INTENSITY_TIMEOUT` - Timeout for Carbon Intensity API requests in seconds (default: 10)

## License

This project is licensed under the MIT License - see the LICENSE file for details.