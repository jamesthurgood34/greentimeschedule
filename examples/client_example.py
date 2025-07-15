#!/usr/bin/env python
"""
Example client for the Green Time Schedule API.
This script demonstrates how to call the API to schedule a batch job.
"""

import asyncio
import json
from datetime import datetime, timedelta
import httpx


async def schedule_job():
    """Schedule a batch job using the Green Time Schedule API."""
    # API endpoint
    api_url = "http://localhost:8000/api/v1/schedule/job"
    
    # Calculate deadline (24 hours from now)
    now = datetime.utcnow()
    deadline = now + timedelta(hours=24)
    deadline_str = deadline.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    # Prepare request data
    request_data = {
        "job_duration_minutes": 120,  # 2 hours
        "deadline_utc": deadline_str,
        "job_name": "data-processing-batch",
        "priority": "low"
    }
    
    print(f"Scheduling job with data: {json.dumps(request_data, indent=2)}")
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(api_url, json=request_data)
            
            if response.status_code == 200:
                result = response.json()
                
                print("\nJob successfully scheduled!")
                print(f"Optimal start time: {result['optimal_start_time']}")
                print(f"Optimal end time: {result['optimal_end_time']}")
                print(f"Carbon intensity: {result['carbon_intensity']} gCO2/kWh ({result['carbon_index']})")
                
                print("\nAlternative slots:")
                for i, slot in enumerate(result['alternative_slots'], 1):
                    print(f"  {i}. {slot['start_time']} to {slot['end_time']} - "
                          f"{slot['carbon_intensity']} gCO2/kWh ({slot['carbon_index']})")
                
                print("\nScheduling metadata:")
                metadata = result['scheduling_metadata']
                print(f"  Periods analyzed: {metadata['periods_analyzed']}")
                print(f"  Forecast confidence: {metadata['forecast_confidence']}")
                print(f"  Cached data age: {metadata['cached_data_age_minutes']} minutes")
                
                return result
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
                
    except Exception as e:
        print(f"Error scheduling job: {str(e)}")
        return None


async def get_carbon_forecast(date):
    """Get carbon intensity forecast for a specific date."""
    api_url = f"http://localhost:8000/api/v1/carbon/forecast/{date}"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(api_url)
            
            if response.status_code == 200:
                result = response.json()
                
                print(f"\nCarbon intensity forecast for {date}:")
                print(f"Data freshness: {result['data_freshness']}")
                
                # Show the first few periods
                print("\nSample periods:")
                for period in result['forecast_periods'][:5]:  # First 5 periods
                    print(f"  Period {period['period']}: {period['start_time']} to {period['end_time']} - "
                          f"{period['intensity_forecast']} gCO2/kWh ({period['intensity_index']})")
                
                print(f"  ... and {len(result['forecast_periods']) - 5} more periods")
                
                return result
            else:
                print(f"Error: {response.status_code}")
                print(response.text)
                return None
                
    except Exception as e:
        print(f"Error getting forecast: {str(e)}")
        return None


async def main():
    """Main function to run the examples."""
    print("Green Time Schedule API Client Example")
    print("======================================")
    
    # First, get carbon forecast for today
    today = datetime.utcnow().strftime("%Y-%m-%d")
    await get_carbon_forecast(today)
    
    # Then schedule a job
    await schedule_job()


if __name__ == "__main__":
    asyncio.run(main())