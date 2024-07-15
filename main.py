from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.responses import RedirectResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Union, Optional, NamedTuple, Tuple, Any
import urllib.parse
from urllib.parse import unquote
import json
import re
from pydantic import BaseModel
import csv
import difflib
from difflib import SequenceMatcher
import unicodedata
import asyncio

app = FastAPI()
@app.get("/")
def root():
    return {"message": "Hello, World!"}

areas = { '香港': { '中西區': ['西環','堅尼地城', '石塘咀', '西營盤', '上環', '中環', '金鐘', '半山', '山頂'], '灣仔': ['灣仔', '銅鑼灣', '跑馬地', '大坑', '掃桿埔', '渣甸山'], '東區': ['天后', '寶馬山', '北角', '鰂魚涌', '西灣河', '筲箕灣', '柴灣', '小西灣'], '南區': ['薄扶林', '香港仔', '鴨脷洲', '黃竹坑', '壽臣山', '淺水灣', '舂磡角', '赤柱', '大潭', '石澳'] }, '九龍': { '油尖旺': ['尖沙咀', '油麻地', '西九龍', '京士柏', '旺角', '大角咀'], '深水埗': ['美孚', '荔枝角', '長沙灣', '深水埗', '石硤尾', '又一村', '大窩坪', '昂船洲'], '九龍城': ['紅磡', '土瓜灣', '馬頭角', '馬頭圍', '啟德', '九龍城', '何文田', '九龍塘', '筆架山'], '黃大仙': ['新蒲崗', '黃大仙', '東頭', '橫頭磡', '樂富', '鑽石山', '慈雲山', '牛池灣'], '觀塘': ['坪石', '九龍灣', '牛頭角', '佐敦谷', '觀塘', '秀茂坪', '藍田', '油塘', '鯉魚門'] }, '新界': { '葵青': ['葵涌', '青衣'], '荃灣': ['荃灣', '梨木樹', '汀九', '深井', '青龍頭', '馬灣', '欣澳'], '屯門': ['大欖涌', '掃管笏', '屯門', '藍地'], '元朗': ['洪水橋', '廈村', '流浮山', '天水圍', '元朗', '新田', '落馬洲', '錦田', '石崗', '八鄉'], '北區': ['粉嶺', '聯和墟', '上水', '石湖墟', '沙頭角', '鹿頸', '烏蛟騰'], '大埔': ['大埔墟', '大埔', '大埔滘', '大尾篤', '船灣', '樟木頭', '企嶺下'], '沙田': ['大圍', '沙田', '火炭', '馬料水', '烏溪沙', '馬鞍山'], '西貢': ['清水灣', '西貢', '大網仔', '將軍澳', '坑口', '調景嶺', '馬游塘'], '離島': ['長洲', '坪洲', '大嶼山', '東涌', '南丫島'] } }

def segment_input(input_str: str) -> List[Dict[str, Union[str, List[str]]]]:
    decoded_input = unquote(input_str)  # Decode URL-encoded input string
    results = []

    # Assuming areas is a predefined dictionary containing areas, districts, and sub-districts
    for area, districts in areas.items():
        for district, sub_districts in districts.items():
            for sub_district in sub_districts:
                if sub_district in decoded_input:
                    # Remove the found sub_district from the input string
                    building_street = decoded_input.replace(sub_district, '').strip()

                    # Remove area, district, and sub_district prefixes if present
                    for prefix in [area, district, sub_district]:
                        if building_street.startswith(prefix):
                            building_street = building_street[len(prefix):].strip()

                    # Split into street and building details
                    if '號' in building_street:
                        street, building_details = building_street.split('號', 1)
                        street += '號'
                    else:
                        street = building_street.strip() + '號'
                        building_details = ''

                    # Append the parsed address components to results
                    results.append({
                        'area': area,
                        'district': district,
                        'sub_district': sub_district,
                        'street': [street],
                        'building': building_details.strip()
                    })

                    return results  # Return early if a specific match is found

    # If no specific match is found, treat the remaining input as a general address
    if decoded_input.strip():
        building_street = decoded_input.strip()

        if '號' in building_street:
            street, building_details = building_street.split('號', 1)
            street += '號'
        else:
            street = building_street.strip() + '號'
            building_details = ''

        results.append({
            'area': '',
            'district': '',
            'sub_district': '',
            'street': [street],
            'building': building_details.strip()
        })

    return results


@app.get("/area/zh-hk/{input_str}")
def segment_address(input_str: str):
    return segment_input(input_str)
hk_districts = [ 'Central and Western', 'Eastern', 'Southern', 'Wan Chai', 'Kowloon City', 'Kwun Tong', 'Sham Shui Po', 'Wong Tai Sin', 'Yau Tsim Mong', 'Kwai Tsing', 'North', 'Sai Kung', 'Sha Tin', 'Tai Po', 'Tsuen Wan', 'Tuen Mun', 'Yuen Long', 'Islands' ]

hk_district_areas = { 'Central and Western': ['Central', 'Sheung Wan', 'Sai Ying Pun', 'Kennedy Town', 'Mid-Levels', 'The Peak', 'Admiralty', 'Lower Peak', 'Upper Central', 'Upper Sheung Wan', 'Western District'], 'Eastern': ['Quarry Bay', 'Chai Wan', 'Shau Kei Wan', 'Sai Wan Ho', 'North Point', 'Fortress Hill', 'Tai Koo Shing', 'Heng Fa Chuen', 'Braemar Hill', 'Aldrich Bay', 'Heng Fa Villa', 'Mount Parker'], 'Southern': ['Aberdeen', 'Ap Lei Chau', 'Stanley', 'Repulse Bay', 'Wong Chuk Hang', 'Pok Fu Lam', 'Deep Water Bay', 'Tin Wan', 'Cyberport', 'Chi Fu Fa Yuen', 'Wah Fu', 'Tai Tam', 'Shek O', 'Big Wave Bay'], 'Wan Chai': ['Wan Chai', 'Causeway Bay', 'Happy Valley', 'Tai Hang', 'Jardine’s Lookout', 'Stubbs Road', 'Broadwood Road', 'Bowen Road'], 'Kowloon City': ['Kowloon City', 'Hung Hom', 'Mong Kok', 'Kowloon Tong', 'To Kwa Wan', 'Ho Man Tin', 'Lok Fu', 'Kowloon Bay', 'Kai Tak', 'Whampoa', 'Hung Hom Bay', 'Ma Tau Wai'], 'Kwun Tong': ['Kwun Tong', 'Lam Tin', 'Yau Tong', 'Ngau Tau Kok', 'Sau Mau Ping', 'Tiu Keng Leng', 'Lei Yue Mun', 'Kowloon Bay Industrial Area', 'Kwun Tong Industrial Area'], 'Sham Shui Po': ['Sham Shui Po', 'Cheung Sha Wan', 'Lai Chi Kok', 'Shek Kip Mei', 'Mei Foo', 'Nam Cheong', 'Yau Yat Tsuen', 'So Uk Estate', 'Wah Lai Estate', 'Un Chau Estate'], 'Wong Tai Sin': ['Wong Tai Sin', 'Diamond Hill', 'Choi Hung', 'Lok Fu', 'Tsz Wan Shan', 'San Po Kong', 'Ngau Chi Wan', 'Wang Tau Hom', 'Chuk Yuen', 'Tung Tau Estate'], 'Yau Tsim Mong': ['Yau Ma Tei', 'Tsim Sha Tsui', 'Jordan', 'Mong Kok', 'Tai Kok Tsui', 'King’s Park', 'West Kowloon', 'Kowloon Park', 'Cherry Street', 'Langham Place'], 'Kwai Tsing': ['Kwai Chung', 'Tsing Yi', 'Kwai Fong', 'Kwai Hing', 'Tsing Yi North', 'Tsing Yi South', 'Cheung Hong', 'Cheung Hang', 'Lai King', 'Greenfield Garden', 'Mayfair Gardens', 'Cheung Wang'], 'North': ['Sheung Shui', 'Fanling', 'Sha Tau Kok', 'Kwu Tung', 'Ta Kwu Ling', 'Lung Yeuk Tau', 'Luk Keng', 'Ping Che', 'Fanling North', 'Shek Wu Hui', 'Wah Ming Estate', 'Ching Ho Estate'], 'Sai Kung': ['Sai Kung', 'Clear Water Bay', 'Tseung Kwan O', 'Hang Hau', 'Pak Tam Chung', 'Silverstrand', 'Po Lam', 'Fei Ngo Shan', 'Sai Kung Town', 'Kau Sai Chau', 'Pak Sha Wan', 'Marina Cove'], 'Sha Tin': ['Sha Tin', 'Ma On Shan', 'Fo Tan', 'Tai Wai', 'Hin Keng', 'Wu Kai Sha', 'Shatin City One', 'Jubilee Garden', 'Lek Yuen Estate', 'Wo Che Estate', 'City One', 'Sha Tin Wai', 'Tate’s Cairn', 'Sha Tin Heights'], 'Tai Po': ['Tai Po', 'Tai Mei Tuk', 'Tai Po Kau', 'Lam Tsuen', 'Plover Cove', 'Hong Lok Yuen', 'Tai Wo Estate', 'Fu Heng Estate', 'Wan Tau Tong', 'Tai Po Industrial Estate', 'Uptown Plaza', 'Greenfield Garden', 'Eightland Gardens'], 'Tsuen Wan': ['Tsuen Wan', 'Tsing Lung Tau', 'Discovery Park', 'Belvedere Garden', 'Sham Tseng', 'Ma Wan', 'Allway Gardens', 'Tsuen Wan West', 'Tsuen King Circuit', 'Nina Tower', 'Clague Garden Estate'], 'Tuen Mun': ['Tuen Mun', 'Castle Peak', 'Sam Shing', 'So Kwun Wat', 'Siu Hong', 'Gold Coast', 'Tuen Mun Town Centre', 'San Hui', 'Butterfly Estate', 'Tai Lam', 'Lung Mun Oasis', 'On Ting Estate'], 'Yuen Long': ['Yuen Long', 'Tin Shui Wai', 'Kam Tin', 'Shui Pin Wai', 'Shap Pat Heung', 'Ping Shan', 'Hung Shui Kiu', 'Fairview Park', 'Yuen Long Town', 'Nam Sang Wai', 'Pat Heung', 'Ha Tsuen'], 'Islands': ['Lantau Island', 'Cheung Chau', 'Peng Chau', 'Lamma Island', 'Discovery Bay', 'Tung Chung', 'Mui Wo', 'Tai O', 'Ngong Ping', 'Po Lin Monastery', 'Silvermine Bay', 'Pui O', 'Chek Lap Kok', 'Sok Kwu Wan', 'Yung Shue Wan', 'Hei Ling Chau'] }

# Create a reverse mapping from area to district
area_to_district = {area.lower(): district for district, areas in hk_district_areas.items() for area in areas}
class AddressOutput(BaseModel):
    street: str = None
    area: str = None
    district: str = None
    region: str = None

# Define a NamedTuple to store the address output
class AddressOutput(NamedTuple):
    area: str = ''
    district: str = ''
    region: str = ''
    street: str = ''

def segment_Einput(input_str: str) -> AddressOutput:
    decoded_input = unquote(input_str)  # Decode URL-encoded input string if necessary

    parts = [part.strip() for part in decoded_input.split(',')]

    result = AddressOutput()

    street_pattern = re.compile(
        r'\d+.*?(Street|Road|Avenue|Lane|Path|Terrace|Drive|Place|Mansion|Boulevard|Court|Square|Garden|Estate)',
        re.IGNORECASE)

    for part in parts:
        if not result.street and street_pattern.search(part):
            result.street = part
        else:
            # Check for area first
            lower_part = part.lower()
            for area, district in area_to_district.items():
                if area in lower_part:
                    result.area = part
                    result.district = district
                    break

            if result.area:
                break

    # If area is not found in the loop, check the entire input string
    if not result.area:
        for area, district in area_to_district.items():
            if area in decoded_input.lower():
                result.area = area.capitalize()
                result.district = district
                break

    # Determine region based on district
    if result.district:
        if result.district in ['Central and Western', 'Eastern', 'Southern', 'Wan Chai']:
            result.region = 'Hong Kong Island'
        elif result.district in ['Kowloon City', 'Kwun Tong', 'Sham Shui Po', 'Wong Tai Sin', 'Yau Tsim Mong']:
            result.region = 'Kowloon'
        else:
            result.region = 'New Territories'

    # If we still don't have all the information, set the entire input as the street
    if not all([result.street, result.area, result.district, result.region]):
        result = AddressOutput(street=decoded_input)

    return result

@app.get("/area/en/{input_str}")
def segment_address(input_str: str):
    return segment_Einput(input_str)

def is_chinese(input_str: str) -> bool:
    for char in input_str:
        if 'CJK' in unicodedata.name(char, ''):
            return True
    return False

@app.get("/area/{input_str}")
async def segment_address(input_str: str):
    if is_chinese(input_str):
        # Redirect to Chinese endpoint
        return RedirectResponse(url=f"/area/zh-hk/{input_str}")
    else:
        # Assumed to English endpoint
        return RedirectResponse(url=f"/area/en/{input_str}")

# Load buildings and streets from text files with UTF-8 encoding
def load_list(file_path: str):
    with open(file_path, 'r', encoding='utf-8') as f:
        items = f.read().splitlines()
    return items

buildings = load_list('Building_merged.txt')
streets = load_list('Street_CSDI.txt')

def jaccard_similarity(str1: str, str2: str) -> float:
    set1, set2 = set(str1), set(str2)
    intersection = set1.intersection(set2)
    union = set1.union(set2)
    return len(intersection) / len(union) if len(union) != 0 else 0

def find_similar_items(input_str: str, items: list, limit: int = 20):
    # Convert input_str to lower case for case-insensitive comparison
    input_str_lower = input_str.lower()
    # Compute Jaccard similarity for each item
    similarities = [(item, jaccard_similarity(input_str_lower, item.lower())) for item in items]
    # Filter out matches with similarity 0
    similarities = [match for match in similarities if match[1] > 0]
    # Sort matches by similarity score (higher scores first)
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:limit]

@app.get("/b/zh-hk/{input_str}")
async def search_buildings(input_str: str, n: int = Query(None, title="Number of output items", ge=1, le=1000)):
    # Decode the URL-encoded input string
    decoded_input_str = urllib.parse.unquote(input_str)
    # Set default n to 20 if not provided
    if n is None:
        n = 20
    matches = find_similar_items(decoded_input_str, buildings, limit=n)
    return JSONResponse(content={"input": decoded_input_str, "matches": [{"building": match[0], "similarity": match[1]} for match in matches]})

@app.get("/s/zh-hk/{input_str}")
async def search_streets(input_str: str, n: int = Query(20, title="Number of output items", ge=1, le=1000)):
    # Decode the URL-encoded input string
    decoded_input_str = urllib.parse.unquote(input_str)
    matches = find_similar_items(decoded_input_str, streets, limit=n)
    return JSONResponse(content={"input": decoded_input_str, "matches": [{"street": match[0], "similarity": match[1]} for match in matches]})

# Precompile regex patterns
street_keywords = ['road', 'street', 'avenue', 'lane', 'bridge', 'tunnel', 'highway', 'route', 'way']
street_keyword_regex = re.compile(r'\b(?:' + '|'.join(street_keywords) + r')\b', re.IGNORECASE)
numeric_ending_regex = re.compile(r'\d+$')

# Load address data from CSV file
def load_address_data(file_path: str) -> List[Tuple[str, str, str, str, str, str, str, str, str, int, int, float, float]]:
    with open(file_path, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [
            (
                row['Area'], row['District'], row['Street'], row['Building'],
                row['BuildingE'], row['StreetE'], row['DistrictE'], row['AreaE'],
                row['GeoAddress'], int(row['Easting']), int(row['Northing']),
                float(row['Lat']), float(row['Lon'])
            )
            for row in reader
        ]

address_data = load_address_data('ALS_DatasetR.csv')

# Custom similarity function with enhanced street name matching
def calculate_custom_similarity(input_str: str, target_str: str) -> Tuple[float, bool]:
    input_normalized = re.sub(r'\s+', '', input_str.lower())
    target_normalized = re.sub(r'\s+', '', target_str.lower())
    target_ends_with_numeric = numeric_ending_regex.search(target_normalized) is not None
    similarity_ratio = difflib.SequenceMatcher(None, input_normalized, target_normalized).ratio()
    if target_ends_with_numeric:
        similarity_ratio *= 1.2
    return similarity_ratio, similarity_ratio > 0.45

# Function to extract number and street name from input
def extract_number_and_street(input_str: str) -> Tuple[str, str]:
    match = re.search(r'\d+$', input_str)
    if match:
        number = match.group()
        street = input_str[:match.start()].strip()
    else:
        number = ''
        street = input_str.strip()
    return number, street

# Optimized function to find similar addresses
def find_similar_addresses(input_str: str, addresses: List[Tuple[str, str, str, str, str, str, str, str, str, int, int, float, float]], lang: str = 'zh-hk') -> List[Dict[str, Any]]:
    input_str_lower = input_str.lower().strip()
    input_number, input_street = extract_number_and_street(input_str_lower)

    matches = []
    for address in addresses:
        if lang == 'en':
            building = address[4].lower()
            street = address[5].lower()
        else:
            building = address[3].lower()
            street = address[2].lower()

        building_similarity, _ = calculate_custom_similarity(input_str_lower, building)
        street_similarity, street_has_street = calculate_custom_similarity(input_street, street)

        if building_similarity > 0.5 or street_has_street:
            combined_similarity = building_similarity + street_similarity
            matches.append({
                "data": address,
                "CombinedSimilarity": combined_similarity
            })

    # Sort matches by CombinedSimilarity in descending order
    matches.sort(key=lambda x: x['CombinedSimilarity'], reverse=True)

    return matches

# Endpoint for address search (Chinese)
@app.get("/alst/zh-hk/{input_str}")
async def address_search(input_str: str, n: int = Query(50, title="Number of output items", ge=1, le=1000)):
    input_str = unquote(input_str)
    matches = await asyncio.to_thread(find_similar_addresses, input_str, address_data)

    if not matches:
        raise HTTPException(status_code=404, detail="No matching addresses found.")

    matches = matches[:n]

    response_data = {
        "input": input_str,
        "matches": [
            {
                "Area": match['data'][0],
                "District": match['data'][1],
                "Street": match['data'][2],
                "Building": match['data'][3],
                "BuildingE": match['data'][4],
                "StreetE": match['data'][5],
                "DistrictE": match['data'][6],
                "AreaE": match['data'][7],
                "GeoAddress": match['data'][8],
                "Easting": match['data'][9],
                "Northing": match['data'][10],
                "Lat": match['data'][11],
                "Lon": match['data'][12],
                "CombinedSimilarity": match['CombinedSimilarity']
            }
            for match in matches
        ]
    }
    return JSONResponse(content=response_data)

# Endpoint for address search (English)
@app.get("/alst/en/{input_str}")
async def address_search_en(input_str: str, n: int = Query(50, title="Number of output items", ge=1, le=1000)):
    input_str = unquote(input_str)
    matches = await asyncio.to_thread(find_similar_addresses, input_str, address_data, 'en')

    if not matches:
        raise HTTPException(status_code=404, detail="No matching addresses found.")

    matches = matches[:n]

    response_data = {
        "input": input_str,
        "matches": [
            {
                "Area": match['data'][0],
                "District": match['data'][1],
                "Street": match['data'][2],
                "Building": match['data'][3],
                "BuildingE": match['data'][4],
                "StreetE": match['data'][5],
                "DistrictE": match['data'][6],
                "AreaE": match['data'][7],
                "GeoAddress": match['data'][8],
                "Easting": match['data'][9],
                "Northing": match['data'][10],
                "Lat": match['data'][11],
                "Lon": match['data'][12],
                "CombinedSimilarity": match['CombinedSimilarity']
            }
            for match in matches
        ]
    }
    return JSONResponse(content=response_data)

# Segment address endpoint
@app.get("/alst/{input_str}")
async def segment_address(input_str: str):
    if input_str.lower().strip().startswith('zh'):
        return RedirectResponse(url=f"/alst/zh-hk/{input_str}")
    else:
        return RedirectResponse(url=f"/alst/en/{input_str}")
