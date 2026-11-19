"""
AtmoSync - Constants & Domain Knowledge Bases
Contains real-world geographical coordinates, Indian APMC market profiles,
commodity thermal/humidity sensitivity guidelines, and risk tiers.
"""

# Indian States and representative agricultural trading hubs/districts
INDIAN_STATES_MARKETS = {
    "Tamil Nadu": [
        {"name": "Koyambedu Wholesale Market Complex", "district": "Chennai", "lat": 13.0694, "lon": 80.1948, "type": "Terminal Mandi", "cap": 12000},
        {"name": "Madurai Central APMC", "district": "Madurai", "lat": 9.9252, "lon": 78.1198, "type": "Regional Hub", "cap": 7500},
        {"name": "Coimbatore Ukkadam Market", "district": "Coimbatore", "lat": 11.0168, "lon": 76.9558, "type": "Wholesale Hub", "cap": 8200},
        {"name": "Tiruchirappalli Gandhi Market", "district": "Tiruchirappalli", "lat": 10.7905, "lon": 78.7047, "type": "Sub-Mandi", "cap": 5000},
        {"name": "Salem Shevapet Agri Market", "district": "Salem", "lat": 11.6643, "lon": 78.1460, "type": "Wholesale Hub", "cap": 6000},
        {"name": "Erode Perundurai Turmeric & Veg Market", "district": "Erode", "lat": 11.3410, "lon": 77.7172, "type": "Commodity Terminal", "cap": 9000},
    ],
    "Karnataka": [
        {"name": "Yeshwanthpur APMC Yard", "district": "Bengaluru", "lat": 13.0238, "lon": 77.5529, "type": "Terminal Mandi", "cap": 15000},
        {"name": "Mysuru Bandipalya APMC", "district": "Mysuru", "lat": 12.2958, "lon": 76.6394, "type": "Regional Hub", "cap": 7000},
        {"name": "Hubballi Amargol APMC", "district": "Dharwad", "lat": 15.3647, "lon": 75.1240, "type": "Regional Hub", "cap": 6800},
        {"name": "Belagavi Central Mandi", "district": "Belagavi", "lat": 15.8497, "lon": 74.4977, "type": "Sub-Mandi", "cap": 4800},
        {"name": "Kolar Fruit & Tomato Market", "district": "Kolar", "lat": 13.1367, "lon": 78.1291, "type": "Specialized Mandi", "cap": 11000},
        {"name": "Mangaluru Baikampady APMC", "district": "Dakshina Kannada", "lat": 12.9141, "lon": 74.8560, "type": "Coastal Mandi", "cap": 5200},
    ],
    "Andhra Pradesh": [
        {"name": "Vijayawada Gollapudi Market Yard", "district": "NTR", "lat": 16.5452, "lon": 80.6033, "type": "Terminal Mandi", "cap": 10500},
        {"name": "Guntur Mirchi & Veg Yard", "district": "Guntur", "lat": 16.3067, "lon": 80.4365, "type": "Specialized Terminal", "cap": 14000},
        {"name": "Visakhapatnam MVP APMC", "district": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185, "type": "Regional Hub", "cap": 7200},
        {"name": "Tirupati Renigunta APMC", "district": "Tirupati", "lat": 13.6288, "lon": 79.4192, "type": "Sub-Mandi", "cap": 4900},
        {"name": "Kurnool C.Camp Market Yard", "district": "Kurnool", "lat": 15.8281, "lon": 78.0373, "type": "Regional Hub", "cap": 5800},
    ],
    "Telangana": [
        {"name": "Bowenpally Agricultural Market", "district": "Hyderabad", "lat": 17.4705, "lon": 78.4812, "type": "Terminal Mandi", "cap": 13500},
        {"name": "Gaddi Annaram Fruit Market (Batasingaram)", "district": "Ranga Reddy", "lat": 17.3457, "lon": 78.6914, "type": "Specialized Mandi", "cap": 12000},
        {"name": "Warangal Enumamula Grain & Veg Market", "district": "Warangal", "lat": 17.9689, "lon": 79.5941, "type": "Regional Hub", "cap": 9500},
        {"name": "Nizamabad Badsi Road APMC", "district": "Nizamabad", "lat": 18.6725, "lon": 78.0941, "type": "Regional Hub", "cap": 6200},
        {"name": "Karimnagar Market Yard", "district": "Karimnagar", "lat": 18.4386, "lon": 79.1288, "type": "Sub-Mandi", "cap": 4600},
    ],
    "Maharashtra": [
        {"name": "Vashi APMC Fruit & Veg Yard", "district": "Navi Mumbai", "lat": 19.0759, "lon": 72.9986, "type": "Terminal Mandi", "cap": 18000},
        {"name": "Pune Gultekdi Market Yard", "district": "Pune", "lat": 18.4988, "lon": 73.8653, "type": "Terminal Mandi", "cap": 13000},
        {"name": "Nashik Panchavati Onion-Tomato APMC", "district": "Nashik", "lat": 20.0076, "lon": 73.7997, "type": "Specialized Terminal", "cap": 14500},
        {"name": "Nagpur Cotton Market APMC", "district": "Nagpur", "lat": 21.1458, "lon": 79.0882, "type": "Regional Hub", "cap": 8500},
        {"name": "Solapur Siddheshwar Market", "district": "Solapur", "lat": 17.6599, "lon": 75.9064, "type": "Regional Hub", "cap": 6400},
        {"name": "Kolhapur Shahu Market Yard", "district": "Kolhapur", "lat": 16.7050, "lon": 74.2433, "type": "Regional Hub", "cap": 7100},
    ],
    "Kerala": [
        {"name": "Kochi Ernakulam Market", "district": "Ernakulam", "lat": 9.9816, "lon": 76.2798, "type": "Terminal Mandi", "cap": 7800},
        {"name": "Thiruvananthapuram Chalai Bazaar", "district": "Thiruvananthapuram", "lat": 8.4842, "lon": 76.9498, "type": "Wholesale Hub", "cap": 6500},
        {"name": "Kozhikode Palayam Central Market", "district": "Kozhikode", "lat": 11.2588, "lon": 75.7804, "type": "Regional Hub", "cap": 6000},
        {"name": "Thrissur Sakthan Thampuran Market", "district": "Thrissur", "lat": 10.5160, "lon": 76.2160, "type": "Regional Hub", "cap": 5400},
    ],
    "Gujarat": [
        {"name": "Ahmedabad Jamalpur APMC", "district": "Ahmedabad", "lat": 23.0125, "lon": 72.5850, "type": "Terminal Mandi", "cap": 14000},
        {"name": "Surat Sardar Market", "district": "Surat", "lat": 21.1702, "lon": 72.8311, "type": "Terminal Mandi", "cap": 12500},
        {"name": "Vadodara Khanderao APMC", "district": "Vadodara", "lat": 22.3072, "lon": 73.1812, "type": "Regional Hub", "cap": 7800},
        {"name": "Rajkot Bedi Yard APMC", "district": "Rajkot", "lat": 22.3039, "lon": 70.8022, "type": "Regional Hub", "cap": 8200},
    ],
    "Delhi": [
        {"name": "Azadpur Mandi", "district": "North Delhi", "lat": 28.7136, "lon": 77.1780, "type": "National Terminal Mandi", "cap": 25000},
        {"name": "Ghazipur Fruit & Veg Sub-Mandi", "district": "East Delhi", "lat": 28.6258, "lon": 77.3312, "type": "Regional Terminal", "cap": 11000},
        {"name": "Okhla Wholesale Mandi", "district": "South East Delhi", "lat": 28.5355, "lon": 77.2711, "type": "Wholesale Hub", "cap": 9000},
        {"name": "Keshopur APMC Market", "district": "West Delhi", "lat": 28.6433, "lon": 77.0867, "type": "Regional Hub", "cap": 7500},
    ],
    "Uttar Pradesh": [
        {"name": "Lucknow Dubagga Mandi", "district": "Lucknow", "lat": 26.8667, "lon": 80.8528, "type": "Terminal Mandi", "cap": 13000},
        {"name": "Kanpur Chakarpur Mandi", "district": "Kanpur Nagar", "lat": 26.4385, "lon": 80.2858, "type": "Terminal Mandi", "cap": 12000},
        {"name": "Agra Sikandra Krishi Utpadan Mandi", "district": "Agra", "lat": 27.2185, "lon": 77.9405, "type": "Regional Hub", "cap": 9500},
        {"name": "Varanasi Chandpur Mandi", "district": "Varanasi", "lat": 25.3176, "lon": 82.9739, "type": "Regional Hub", "cap": 8000},
        {"name": "Prayagraj Mundera Mandi", "district": "Prayagraj", "lat": 25.4358, "lon": 81.8463, "type": "Regional Hub", "cap": 7200},
    ],
    "West Bengal": [
        {"name": "Kolkata Mechua Fruit Mandi", "district": "Kolkata", "lat": 22.5850, "lon": 88.3610, "type": "Terminal Mandi", "cap": 16000},
        {"name": "Kolkata Posta Wholesale Market", "district": "Kolkata", "lat": 22.5878, "lon": 88.3552, "type": "Terminal Mandi", "cap": 13500},
        {"name": "Siliguri Regulated Market Yard", "district": "Darjeeling", "lat": 26.7271, "lon": 88.3953, "type": "Strategic Cross-border Mandi", "cap": 9000},
        {"name": "Howrah Ramrajatala Market", "district": "Howrah", "lat": 22.5958, "lon": 88.2636, "type": "Regional Hub", "cap": 7400},
        {"name": "Bardhaman Central APMC", "district": "Purba Bardhaman", "lat": 23.2324, "lon": 87.8615, "type": "Agri Hub", "cap": 6500},
    ]
}

# 15 Core Commodities and realistic baseline storage & pricing parameters
BASE_COMMODITIES = {
    # Fruits
    "Avocado": {
        "category": "Fruit",
        "base_price": 140.0,
        "opt_temp": 6.0,
        "min_temp": 4.0,
        "max_temp": 12.0,
        "opt_humidity": 88.0,
        "max_humidity": 95.0,
        "shelf_life_days": 14,
        "sensitivity": "High",
        "varieties": ["Hass Premium", "Fuerte Standard", "Pinkerton Organic", "Grown-in-Nilgiris Grade-A"]
    },
    "Mango": {
        "category": "Fruit",
        "base_price": 95.0,
        "opt_temp": 12.0,
        "min_temp": 10.0,
        "max_temp": 15.0,
        "opt_humidity": 85.0,
        "max_humidity": 90.0,
        "shelf_life_days": 12,
        "sensitivity": "Critical",
        "varieties": ["Alphonso Ratnagiri", "Kesar Gujarat", "Banganapalli AP", "Dasheri Malihabad", "Totapuri Process"]
    },
    "Banana": {
        "category": "Fruit",
        "base_price": 38.0,
        "opt_temp": 13.5,
        "min_temp": 12.0,
        "max_temp": 16.0,
        "opt_humidity": 90.0,
        "max_humidity": 95.0,
        "shelf_life_days": 10,
        "sensitivity": "High",
        "varieties": ["Grand Naine Export", "Robusta Premium", "Nendran Kerala", "Yellaki Baby", "Red Banana Special"]
    },
    "Apple": {
        "category": "Fruit",
        "base_price": 130.0,
        "opt_temp": 2.0,
        "min_temp": 0.0,
        "max_temp": 5.0,
        "opt_humidity": 90.0,
        "max_humidity": 95.0,
        "shelf_life_days": 60,
        "sensitivity": "Moderate",
        "varieties": ["Kashmir Delicious", "Kinnaur Royal", "Shimla Golden", "Washington Red Import"]
    },
    "Orange": {
        "category": "Fruit",
        "base_price": 55.0,
        "opt_temp": 7.0,
        "min_temp": 4.0,
        "max_temp": 10.0,
        "opt_humidity": 88.0,
        "max_humidity": 92.0,
        "shelf_life_days": 25,
        "sensitivity": "Moderate",
        "varieties": ["Nagpur Santra Grade-A", "Kinnow Punjab", "Coorg Mandarin", "Mosambi Sweet Lime"]
    },
    "Grapes": {
        "category": "Fruit",
        "base_price": 85.0,
        "opt_temp": 1.0,
        "min_temp": -0.5,
        "max_temp": 3.0,
        "opt_humidity": 92.0,
        "max_humidity": 95.0,
        "shelf_life_days": 35,
        "sensitivity": "High",
        "varieties": ["Nashik Thompson Seedless", "Tas-A-Ganesh Special", "Sonaka Green", "Sharad Seedless Black"]
    },
    "Papaya": {
        "category": "Fruit",
        "base_price": 32.0,
        "opt_temp": 11.0,
        "min_temp": 8.0,
        "max_temp": 14.0,
        "opt_humidity": 85.0,
        "max_humidity": 90.0,
        "shelf_life_days": 9,
        "sensitivity": "Critical",
        "varieties": ["Red Lady 786", "Taiwan Semi-Dwarf", "Pusa Dwarf", "Honey Dew Golden"]
    },

    # Vegetables
    "Tomato": {
        "category": "Vegetable",
        "base_price": 35.0,
        "opt_temp": 11.0,
        "min_temp": 8.0,
        "max_temp": 15.0,
        "opt_humidity": 88.0,
        "max_humidity": 92.0,
        "shelf_life_days": 10,
        "sensitivity": "Critical",
        "varieties": ["Hybrid Vaishnavi", "Desi Round Acidic", "Roma Plum Salad", "Avinash-2 Green-shoulder"]
    },
    "Onion": {
        "category": "Vegetable",
        "base_price": 28.0,
        "opt_temp": 1.5,
        "min_temp": 0.0,
        "max_temp": 25.0,
        "opt_humidity": 65.0,
        "max_humidity": 75.0,
        "shelf_life_days": 75,
        "sensitivity": "Low",
        "varieties": ["Lasalgaon Red Nashik", "Garwa Rabi Storage", "Pune Fursungi", "White Onion Export", "Bellary Onion"]
    },
    "Potato": {
        "category": "Vegetable",
        "base_price": 22.0,
        "opt_temp": 7.0,
        "min_temp": 4.0,
        "max_temp": 10.0,
        "opt_humidity": 90.0,
        "max_humidity": 95.0,
        "shelf_life_days": 90,
        "sensitivity": "Low",
        "varieties": ["Kufri Jyoti Table", "Kufri Chipsona Industrial", "Kufri Pukhraj Early", "Lal Gulab Red"]
    },
    "Brinjal": {
        "category": "Vegetable",
        "base_price": 26.0,
        "opt_temp": 11.5,
        "min_temp": 9.0,
        "max_temp": 14.0,
        "opt_humidity": 90.0,
        "max_humidity": 95.0,
        "shelf_life_days": 8,
        "sensitivity": "High",
        "varieties": ["Bhanta Big Purple", "Green Striped Long", "Udupi Mattu Gulla", "Manjri Gota Small Round"]
    },
    "Cabbage": {
        "category": "Vegetable",
        "base_price": 20.0,
        "opt_temp": 1.0,
        "min_temp": 0.0,
        "max_temp": 4.0,
        "opt_humidity": 95.0,
        "max_humidity": 98.0,
        "shelf_life_days": 28,
        "sensitivity": "Moderate",
        "varieties": ["Golden Acre Standard", "Pride of India Early", "Red Rock Gourmet", "Chinese Cabbage Napa"]
    },
    "Green Chilli": {
        "category": "Vegetable",
        "base_price": 60.0,
        "opt_temp": 9.0,
        "min_temp": 7.0,
        "max_temp": 12.0,
        "opt_humidity": 90.0,
        "max_humidity": 95.0,
        "shelf_life_days": 14,
        "sensitivity": "High",
        "varieties": ["Guntur Sannam Hot", "Jwala Long Slender", "Byadgi Wrinkled Medium", "Kanthari Bird Eye"]
    },
    "Carrot": {
        "category": "Vegetable",
        "base_price": 34.0,
        "opt_temp": 1.0,
        "min_temp": 0.0,
        "max_temp": 3.0,
        "opt_humidity": 95.0,
        "max_humidity": 98.0,
        "shelf_life_days": 40,
        "sensitivity": "Moderate",
        "varieties": ["Ooty Hill Sweet Orange", "Pusa Rudhira Red", "Nantes Cylindrical", "Kuroda Kuroda Special"]
    },
    "Cauliflower": {
        "category": "Vegetable",
        "base_price": 30.0,
        "opt_temp": 1.0,
        "min_temp": 0.0,
        "max_temp": 3.0,
        "opt_humidity": 95.0,
        "max_humidity": 98.0,
        "shelf_life_days": 18,
        "sensitivity": "High",
        "varieties": ["Pusa Snowball Compact", "Early Kunwari Summer", "Pusa Deepali Autumn", "Purple Romanesco Hybrid"]
    }
}

SHIPMENT_STATUSES = ["In Transit", "Delivered", "Delayed", "At Risk", "Completed"]

SENSITIVITY_WEIGHTS = {
    "Low": 0.65,
    "Moderate": 1.0,
    "High": 1.35,
    "Critical": 1.70
}

RISK_TIERS = {
    "Low": {"min": 0, "max": 24, "color": "#16A34A", "label": "Low Risk"},
    "Moderate": {"min": 25, "max": 49, "color": "#3B82F6", "label": "Moderate Risk"},
    "High": {"min": 50, "max": 74, "color": "#F59E0B", "label": "High Risk"},
    "Critical": {"min": 75, "max": 100, "color": "#DC2626", "label": "Critical Risk"}
}

OPPORTUNITY_TIERS = {
    "High Opportunity": {"min_benefit": 40000, "color": "#16A34A"},
    "Moderate Opportunity": {"min_benefit": 15000, "color": "#12B8A6"},
    "Low Opportunity": {"min_benefit": 1, "color": "#F59E0B"},
    "Not Recommended": {"min_benefit": -9999999, "color": "#64748B"}
}
