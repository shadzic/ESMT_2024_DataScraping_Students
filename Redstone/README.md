# Grin - E-scooter and E-bike Sharing Service

## Introduction

- **Grin**: An e-scooter and e-bike-sharing service located in **Berlin**, tailored for tourists and locals.
- **Location**: Berlin is an ideal hub for this service due to its famous tourist attractions such as **Brandenburg Gate** and **Alexanderplatz**.
- **Unique Feature**: Grin provides in-app navigation with real-time vehicle locations and offers users discounts at partner restaurants and tourist spots.
- **Target Audience**: Designed for tourists and locals who want eco-friendly, affordable, and quick transportation options.

### Problems Solved
- **For Users**: Grin provides a cost-effective, green transportation method.
- **For the Company**: Reduces operational costs by encouraging users to park near partnered businesses, allowing more strategic vehicle placement and minimizing logistics.

### Future Growth
- Expand to more cities.
- Optimize vehicle placement using data-driven insights to improve service quality.
- Build more partnerships with local businesses.

### Opportunities
- Use data to drive expansion to new cities.
- Establish additional partnerships with restaurants, cafes, and tourist attractions to drive business and provide added value to users.

## Why Grin?

### Business Idea
**Berlin** is known for its vibrant tourism and eco-friendly culture. Grin fills a gap in the market by offering a rental service that benefits both users and local businesses, providing a sustainable and cost-effective transport solution.

### Name Choice
We chose **Grin** because it captures the joy and convenience of our service. Whether you're zipping around Berlin or saving money with our discounts, "Grin" reflects the positive experience we want to offer.

### Target Audience
Our service targets both **tourists** who want to explore the city in an eco-friendly way and **residents** looking for a fast and convenient commute.

### Problems Addressed
1. **For Users**: Affordable, green transportation.
2. **For Grin**: Reduced operational costs through strategic vehicle placement and discounts at partner businesses.

### Strategic Decisions for Future Success
- **Partnerships**: We collaborate with local restaurants and tourist attractions, incentivizing users to park near these spots and helping us streamline operations.
- **Data-Driven Expansion**: We plan to expand to other cities using insights from the data we collect to optimize vehicle placement and user experience.

### Challenges
The biggest challenge is maintaining a balance between **vehicle availability** and **operational efficiency**. Ensuring that vehicles are charged and available during peak times while keeping users satisfied is a constant challenge.

### Opportunities
- **Expansion**: We can grow into new cities and offer advanced features in our app.
- **Data Utilization**: The data we gather will help us improve routes, optimize vehicle placement, and enhance user satisfaction.

### Can Data Save or Expand Grin?
Yes! **Data** is essential to Grin’s future. By analyzing user patterns, we can optimize vehicle placement, create partnerships with key businesses, and ensure our service remains efficient and user-friendly as we expand.

---

## Project Overview: Data Scraping & Processing

This project is part of a data scraping course where we used various APIs to build Grin’s data ecosystem. Data from APIs such as:

- **Meteostat**: Weather data API.
- **Foursquare**: Business and place data API.
- **Google APIs**: Location and routing services.
- **Kaggle Weather Dataset**: Historical weather and rental business data.

The collected data was cleaned and processed to make data-driven decisions that optimize vehicle placement and user experience.

---

## Data Cleaning & Processing (3 Points)

**Recommended Deadline**: October 18th - October 21st  
**Final Deadline**: October 24th at 01:29 PM CET

To make informed business decisions, we cleaned and processed the collected data, filled missing values, and merged datasets from different sources. This allowed us to organize the data into structured formats like CSV, Excel, and HTML files. These datasets were essential for making predictions, optimizing routes, and enhancing user experience.

We generated multiple visualizations and simulations using **Streamlit** to interact with the data.

---

## Project Structure

The project is organized into the following directories and scripts:
```bash
Redstone/
│
├── data/                              # Contains all the project saved datasets
│
├── notebooks/                         # Jupyter notebooks for analysis and exploration
│   ├── AnalysisExploratory.ipynb      # Exploratory data analysis
│   ├── DataAnalysis.ipynb             # Detailed data analysis
│   └── ExplorationAPI.ipynb           # API exploration notebook
│
├── scripts/                           # Python scripts
│   ├── maps.py                        # Script to generate map visualizations
│   └── project_vis.py                 # Streamlit visualization script
│
├── README.md                          # Project README file
│
└── requirements.txt                   # Python dependencies for the project

---
```
## Running the Streamlit App

To run the **Streamlit** app and visualize the data interactively:

1. Install the required Python packages:
```bash
pip install -r Redstone/requirements.txt
```

2.	Launch the Streamlit app:
```bash
streamlit run Redstone/scripts/project_vis.py
```
