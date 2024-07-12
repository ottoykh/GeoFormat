from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Union
from urllib.parse import unquote
import re

# Define your data for area and district mappings here
areas = {
    '香港': {
        '中西區': ['堅尼地城', '石塘咀', '西營盤', '上環', '中環', '金鐘', '半山', '山頂'],
        '灣仔': ['灣仔', '銅鑼灣', '跑馬地', '大坑', '掃桿埔', '渣甸山'],
        '東區': ['天后', '寶馬山', '北角', '鰂魚涌', '西灣河', '筲箕灣', '柴灣', '小西灣'],
        '南區': ['薄扶林', '香港仔', '鴨脷洲', '黃竹坑', '壽臣山', '淺水灣', '舂磡角', '赤柱', '大潭', '石澳']
    },
    '九龍': {
        '油尖旺': ['尖沙咀', '油麻地', '西九龍', '京士柏', '旺角', '大角咀'],
        '深水埗': ['美孚', '荔枝角', '長沙灣', '深水埗', '石硤尾', '又一村', '大窩坪', '昂船洲'],
        '九龍城': ['紅磡', '土瓜灣', '馬頭角', '馬頭圍', '啟德', '九龍城', '何文田', '九龍塘', '筆架山'],
        '黃大仙': ['新蒲崗', '黃大仙', '東頭', '橫頭磡', '樂富', '鑽石山', '慈雲山', '牛池灣'],
        '觀塘': ['坪石', '九龍灣', '牛頭角', '佐敦谷', '觀塘', '秀茂坪', '藍田', '油塘', '鯉魚門']
    },
    '新界': {
        '葵青': ['葵涌', '青衣'],
        '荃灣': ['荃灣', '梨木樹', '汀九', '深井', '青龍頭', '馬灣', '欣澳'],
        '屯門': ['大欖涌', '掃管笏', '屯門', '藍地'],
        '元朗': ['洪水橋', '廈村', '流浮山', '天水圍', '元朗', '新田', '落馬洲', '錦田', '石崗', '八鄉'],
        '北區': ['粉嶺', '聯和墟', '上水', '石湖墟', '沙頭角', '鹿頸', '烏蛟騰'],
        '大埔': ['大埔墟', '大埔', '大埔滘', '大尾篤', '船灣', '樟木頭', '企嶺下'],
        '沙田': ['大圍', '沙田', '火炭', '馬料水', '烏溪沙', '馬鞍山'],
        '西貢': ['清水灣', '西貢', '大網仔', '將軍澳', '坑口', '調景嶺', '馬游塘'],
        '離島': ['長洲', '坪洲', '大嶼山', '東涌', '南丫島']
    }
}

hk_districts = [
    'Central and Western', 'Eastern', 'Southern', 'Wan Chai',
    'Kowloon City', 'Kwun Tong', 'Sham Shui Po', 'Wong Tai Sin', 'Yau Tsim Mong',
    'Kwai Tsing', 'North', 'Sai Kung', 'Sha Tin', 'Tai Po', 'Tsuen Wan',
    'Tuen Mun', 'Yuen Long', 'Islands'
]

hk_district_areas = {
    'Central and Western': ['Central', 'Sheung Wan', 'Sai Ying Pun', 'Kennedy Town', 'Mid-Levels', 'The Peak', 'Admiralty', 'Lower Peak', 'Upper Central', 'Upper Sheung Wan', 'Western District'],
    'Eastern': ['Quarry Bay', 'Chai Wan', 'Shau Kei Wan', 'Sai Wan Ho', 'North Point', 'Fortress Hill', 'Tai Koo Shing', 'Heng Fa Chuen', 'Braemar Hill', 'Aldrich Bay', 'Heng Fa Villa', 'Mount Parker'],
    'Southern': ['Aberdeen', 'Ap Lei Chau', 'Stanley', 'Repulse Bay', 'Wong Chuk Hang', 'Pok Fu Lam', 'Deep Water Bay', 'Tin Wan', 'Cyberport', 'Chi Fu Fa Yuen', 'Wah Fu', 'Tai Tam', 'Shek O', 'Big Wave Bay'],
    'Wan Chai': ['Wan Chai', 'Causeway Bay', 'Happy Valley', 'Tai Hang', 'Jardine’s Lookout', 'Stubbs Road', 'Broadwood Road', 'Bowen Road'],
    'Kowloon City': ['Kowloon City', 'Hung Hom', 'Mong Kok', 'Kowloon Tong', 'To Kwa Wan', 'Ho Man Tin', 'Lok Fu', 'Kowloon Bay', 'Kai Tak', 'Whampoa', 'Hung Hom Bay', 'Ma Tau Wai'],
    'Kwun Tong': ['Kwun Tong', 'Lam Tin', 'Yau Tong', 'Ngau Tau Kok', 'Sau Mau Ping', 'Tiu Keng Leng', 'Lei Yue Mun', 'Kowloon Bay Industrial Area', 'Kwun Tong Industrial Area'],
    'Sham Shui Po': ['Sham Shui Po', 'Cheung Sha Wan', 'Lai Chi Kok', 'Shek Kip Mei', 'Mei Foo', 'Nam Cheong', 'Yau Yat Tsuen', 'So Uk Estate', 'Wah Lai Estate', 'Un Chau Estate'],
    'Wong Tai Sin': ['Wong Tai Sin', 'Diamond Hill', 'Choi Hung', 'Lok Fu', 'Tsz Wan Shan', 'San Po Kong', 'Ngau Chi Wan', 'Wang Tau Hom', 'Chuk Yuen', 'Tung Tau Estate'],
    'Yau Tsim Mong': ['Yau Ma Tei', 'Tsim Sha Tsui', 'Jordan', 'Mong Kok', 'Tai Kok Tsui', 'King’s Park', 'West Kowloon', 'Kowloon Park', 'Cherry Street', 'Langham Place'],
    'Kwai Tsing': ['Kwai Chung', 'Tsing Yi', 'Kwai Fong', 'Kwai Hing', 'Tsing Yi North', 'Tsing Yi South', 'Cheung Ching Estate', 'Greenfield Garden'],
    'North': ['Fanling', 'Sheung Shui', 'Sha Tau Kok', 'Kwu Tung', 'Luen Wo Hui', 'Kwan Tei', 'Lo Wu', 'Ping Che', 'Kam Tsin'],
    'Sai Kung': ['Sai Kung', 'Tseung Kwan O', 'Clear Water Bay', 'Hang Hau', 'Pak Sha Wan', 'Hoi Ha', 'Sai Wan', 'Tap Mun', 'Sheung Sze Wan', 'Chek Keng', 'Tai Mong Tsai', 'Kau Sai Chau'],
    'Sha Tin': ['Sha Tin', 'Ma On Shan', 'Fo Tan', 'Tai Wai', 'Wu Kai Sha', 'Yuen Chau Kok', 'Shing Mun River', 'Shui Chuen O'],
    'Tai Po': ['Tai Po', 'Tai Po Market', 'Tai Po Kau', 'Tai Po Hui', 'Tai Po Industrial Estate', 'Sam Mun Tsai', 'Lam Tsuen', 'Yuen Chau Tsai', 'Chung Tsai Yuen', 'Ma Wo', 'Shuen Wan', 'Yuen Leng', 'Fung Yuen'],
    'Tsuen Wan': ['Tsuen Wan', 'Sham Tseng', 'Ting Kau', 'Tai Wo Hau', 'Cheung Shan', 'Belvedere Garden', 'Discovery Park', 'Nina Tower'],
    'Tuen Mun': ['Tuen Mun', 'Tai Hing', 'Yuet Wu', 'Butterfly', 'San Hui', 'Tsing Shan', 'Tuen Mun Town Centre', 'On Ting', 'Siu Hong', 'Tsing Chung Koon', 'Tuen Mun New Town', 'Tuen Mun Industrial Area'],
    'Yuen Long': ['Yuen Long', 'Tin Shui Wai', 'Kam Tin', 'Pat Heung', 'Shui Pin Wai', 'Tong Yan San Tsuen', 'Ha Tsuen', 'Hung Shui Kiu', 'Ping Shan', 'Shap Pat Heung', 'Yuen Long Town'],
    'Islands': ['Cheung Chau', 'Peng Chau', 'Mui Wo', 'Discovery Bay', 'Tung Chung', 'Lantau Island', 'South Lantau', 'Lamma Island', 'Tai O']
}

# Reverse mapping from sub-district to district and area for English addresses
area_to_district = {area.lower(): district for district, areas in areas.items() for area in areas}

# Define FastAPI instance
app = FastAPI()

# Pydantic model for Chinese address output
class ChineseAddressOutput(BaseModel):
    area: str
    district: str
    sub_district: str
    street: List[str]
    building: str

# Pydantic model for English address output
class EnglishAddressOutput(BaseModel):
    street: str
    area: str
    district: str
    region: str

# Function to segment Chinese address input
def segment_chinese_address(input_str: str) -> List[Dict[str, Union[str, List[str]]]]:
    decoded_input = unquote(input_str)  # Decode URL-encoded input string
    results = []

    # Regular expression to match sub-districts and street names
    sub_districts = sum([sub_districts for districts in areas.values() for sub_districts in districts.values()], [])

    for area, districts in areas.items():
        for district, sub_district_list in districts.items():
            for sub_district in sub_district_list:
                if sub_district in decoded_input:
                    # Remove sub-district from input string
                    building_street = decoded_input.replace(sub_district, '').strip()

                    # Extract street and building details
                    match = re.search(r'(\d+.*?號)', building_street)
                    if match:
                        street = match.group(0)
                        building = building_street.replace(street, '').strip()
                    else:
                        street = building_street
                        building = ''

                    results.append({
                        'area': area,
                        'district': district,
                        'sub_district': sub_district,
                        'street': [street],
                        'building': building
                    })
                    return results

    # If no specific match found, treat as a general address
    if decoded_input.strip():
        results.append({
            'area': '',
            'district': '',
            'sub_district': '',
            'street': [decoded_input.strip()],
            'building': ''
        })

    return results

# Function to segment English address input
def segment_english_address(input_str: str) -> EnglishAddressOutput:
    parts = [part.strip() for part in input_str.split(',')]

    street_pattern = re.compile(
        r'\d+.*?(Street|Road|Avenue|Lane|Path|Terrace|Drive|Place|Mansion|Boulevard|Court|Square|Garden|Estate)',
        re.IGNORECASE)

    result = EnglishAddressOutput()

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
            if area in input_str.lower():
                result.area = area.capitalize()
                result.district = district
                break

    # Determine region based on district
    if result.district:
        if result.district in ['中西區', '東區', '南區', '灣仔']:
            result.region = 'Hong Kong Island'
        elif result.district in ['九龍城', '油尖旺', '深水埗', '黃大仙', '觀塘']:
            result.region = 'Kowloon'
        else:
            result.region = 'New Territories'

    return result

# FastAPI endpoints
@app.get("/")
def root():
    return {"message": "Hello, World!"}

@app.get("/area/zh-hk/{input_str}", response_model=List[ChineseAddressOutput])
def segment_chinese_address_api(input_str: str):
    result = segment_chinese_address(input_str)
    return result

@app.get("/area/en/{input_str}", response_model=EnglishAddressOutput)
def segment_english_address_api(input_str: str):
    result = segment_english_address(input_str)
    return result
