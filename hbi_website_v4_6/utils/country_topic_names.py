"""Country labels excluded only from the top collaborative-topic summary.

Country/territory names are a local snapshot of .NET RegionInfo English names
and Scopus affiliation-country labels (2026-09-11), plus common aliases.
No runtime dependency on Windows, a country package, or network access.
Whole-label matching preserves research phrases such as "guinea pig".
"""

import unicodedata


def normalize_country_label(value: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", str(value).casefold())
        if char.isalnum()
    )


COUNTRY_TOPIC_NAMES = frozenset(
    normalize_country_label(name)
    for name in """\
Afghanistan
Albania
Algeria
American Samoa
Andorra
Angola
Anguilla
Antigua & Barbuda
Antigua and Barbuda
Argentina
Armenia
Aruba
Australia
Austria
Azerbaijan
Bahamas
Bahrain
Bangladesh
Barbados
Belarus
Belgium
Belize
Benin
Bermuda
Bhutan
Bolivia
Bolivia, Plurinational State of
Bonaire, Sint Eustatius and Saba
Bosnia & Herzegovina
Bosnia and Herzegovina
Botswana
Bouvet Island
Brazil
Britain
British Indian Ocean Territory
British Virgin Islands
Brunei
Brunei Darussalam
Bulgaria
Burkina Faso
Burma
Burundi
Cabo Verde
Cambodia
Cameroon
Canada
Cape Verde
Cayman Islands
Central African Republic
Chad
Chile
China
Christmas Island
Cocos (Keeling) Islands
Colombia
Comoros
Congo
Congo (DRC)
Congo, Democratic Republic of the
Cook Islands
Costa Rica
Cote d'Ivoire
Croatia
Cuba
Curaçao
Cyprus
Czech Republic
Czechia
Czechoslovakia
Côte d’Ivoire
DR Congo
DRC
Democratic People's Republic of Korea
Democratic Republic Congo
Democratic Republic of the Congo
Denmark
Djibouti
Dominica
Dominican Republic
East Timor
Ecuador
Egypt
El Salvador
Equatorial Guinea
Eritrea
Estonia
Eswatini
Ethiopia
Falkland Islands
Faroe Islands
Federated States of Micronesia
Fiji
Finland
France
French Guiana
French Polynesia
French Southern Territories
Gabon
Gambia
Georgia
Germany
Ghana
Gibraltar
Great Britain
Greece
Greenland
Grenada
Guadeloupe
Guam
Guatemala
Guernsey
Guinea
Guinea-Bissau
Guyana
Haiti
Heard Island and McDonald Islands
Holy See
Honduras
Hong Kong
Hong Kong SAR
Hungary
Iceland
India
Indonesia
Iran
Iran, Islamic Republic of
Iraq
Ireland
Islamic Republic of Iran
Isle of Man
Israel
Italy
Ivory Coast
Jamaica
Japan
Jersey
Jordan
Kazakhstan
Kenya
Kiribati
Korea
Korea, Democratic People's Republic of
Korea, Republic of
Kosovo
Kuwait
Kyrgyzstan
Lao PDR
Lao People's Democratic Republic
Laos
Latvia
Lebanon
Lesotho
Liberia
Libya
Liechtenstein
Lithuania
Luxembourg
Macao
Macao SAR
Macau
Macedonia
Madagascar
Malawi
Malaysia
Maldives
Mali
Malta
Marshall Islands
Martinique
Mauritania
Mauritius
Mayotte
Mexico
Micronesia
Micronesia, Federated States of
Moldova
Moldova, Republic of
Monaco
Mongolia
Montenegro
Montserrat
Morocco
Mozambique
Myanmar
Namibia
Nauru
Nepal
Netherlands
Netherlands Antilles
New Caledonia
New Zealand
Nicaragua
Niger
Nigeria
Niue
Norfolk Island
North Korea
North Macedonia
Northern Mariana Islands
Norway
Oman
PR China
Pakistan
Palau
Palestine
Palestinian Authority
Palestinian Territories
Panama
Papua New Guinea
Paraguay
People's Republic of China
Peru
Philippines
Pitcairn Islands
Poland
Portugal
Puerto Rico
Qatar
Republic of China
Republic of Korea
Republic of the Congo
Romania
Russia
Russian Federation
Rwanda
Réunion
Saint Barthelemy
Saint Helena, Ascension and Tristan da Cunha
Saint Kitts and Nevis
Saint Lucia
Saint Martin
Saint Pierre and Miquelon
Saint Vincent and the Grenadines
Samoa
San Marino
Sao Tome and Principe
Saudi Arabia
Senegal
Serbia
Seychelles
Sierra Leone
Singapore
Sint Maarten
Slovakia
Slovenia
Solomon Islands
Somalia
South Africa
South Georgia and the South Sandwich Islands
South Korea
South Sudan
Soviet Union
Spain
Sri Lanka
St Helena, Ascension, Tristan da Cunha
St. Barthélemy
St. Kitts & Nevis
St. Lucia
St. Martin
St. Pierre & Miquelon
St. Vincent & Grenadines
State of Palestine
Sudan
Suriname
Svalbard & Jan Mayen
Svalbard and Jan Mayen
Swaziland
Sweden
Switzerland
Syria
Syrian Arab Republic
São Tomé & Príncipe
Taiwan
Tajikistan
Tanzania
Tanzania, United Republic of
Thailand
The Bahamas
The Gambia
Timor-Leste
Togo
Tokelau
Tonga
Trinidad & Tobago
Trinidad and Tobago
Tunisia
Turkey
Turkmenistan
Turks & Caicos Islands
Turks and Caicos Islands
Tuvalu
Türkiye
U.S. Outlying Islands
U.S. Virgin Islands
UAE
UK
US
USA
USSR
Uganda
Ukraine
United Arab Emirates
United Kingdom
United Republic of Tanzania
United States
United States Minor Outlying Islands
United States Virgin Islands
United States of America
Uruguay
Uzbekistan
Vanuatu
Vatican
Vatican City
Venezuela
Venezuela, Bolivarian Republic of
Viet Nam
Vietnam
Wallis & Futuna
Wallis and Futuna
Yemen
Yugoslavia
Zaire
Zambia
Zimbabwe
Åland Islands
""".splitlines()
)
