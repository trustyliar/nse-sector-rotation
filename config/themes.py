"""Indian market themes on top of Yahoo's (US-style) industry labels. Edit freely."""
RENAME = {
    "Confectioners": "Sugar", "Luxury Goods": "Jewellery", "Aerospace & Defense": "Defence",
    "Drug Manufacturers - Specialty & Generic": "Pharma", "Drug Manufacturers - General": "Pharma",
    "Credit Services": "NBFC", "Mortgage Finance": "Housing Finance", "Capital Markets": "Capital Markets",
    "Asset Management": "Asset Management", "Information Technology Services": "IT Services",
    "Software - Application": "Software", "Software - Infrastructure": "Software",
    "Engineering & Construction": "Infra & Construction", "Specialty Industrial Machinery": "Capital Goods",
    "Electrical Equipment & Parts": "Electricals & Power Equipment", "Auto Parts": "Auto Ancillaries",
    "Auto Manufacturers": "Automobiles", "Farm & Heavy Construction Machinery": "Tractors & CVs",
    "Real Estate - Development": "Real Estate", "Real Estate Services": "Real Estate",
    "Real Estate - Diversified": "Real Estate", "Medical Care Facilities": "Hospitals",
    "Diagnostics & Research": "Diagnostics", "Agricultural Inputs": "Fertilisers & Agrochem",
    "Textile Manufacturing": "Textiles", "Apparel Manufacturing": "Textiles", "Building Materials": "Cement",
    "Utilities - Regulated Electric": "Power", "Utilities - Independent Power Producers": "Power",
    "Utilities - Renewable": "Renewables", "Solar": "Renewables", "Oil & Gas Refining & Marketing": "Oil & Gas",
    "Oil & Gas Integrated": "Oil & Gas", "Oil & Gas E&P": "Oil & Gas", "Utilities - Regulated Gas": "Gas Distribution",
    "Lodging": "Hotels", "Restaurants": "QSR & Restaurants", "Packaged Foods": "FMCG Foods",
    "Household & Personal Products": "FMCG Personal Care", "Insurance - Life": "Insurance",
    "Insurance - Property & Casualty": "Insurance", "Insurance - Diversified": "Insurance",
    "Telecom Services": "Telecom", "Communication Equipment": "Telecom Equipment",
    "Electronic Components": "Electronics Manufacturing", "Consumer Electronics": "Electronics Manufacturing",
    "Marine Shipping": "Shipping", "Integrated Freight & Logistics": "Logistics", "Railroads": "Railways",
    "Other Industrial Metals & Mining": "Metals & Mining", "Aluminum": "Metals & Mining", "Copper": "Metals & Mining",
    "Thermal Coal": "Metals & Mining", "Furnishings, Fixtures & Appliances": "Consumer Durables",
    "Building Products & Equipment": "Building Products", "Beverages - Wineries & Distilleries": "Liquor",
    "Beverages - Brewers": "Liquor", "Internet Retail": "Internet & E-commerce",
    "Internet Content & Information": "Internet & E-commerce",
}
PSU_BANKS = {"SBIN", "BANKBARODA", "PNB", "CANBK", "UNIONBANK", "INDIANB", "BANKINDIA", "IOB", "UCOBANK",
             "CENTRALBK", "MAHABANK", "PSB"}
SYMBOL_THEME = {s: "Railways" for s in ("IRFC", "RVNL", "IRCON", "RAILTEL", "TITAGARH", "JWL", "TEXRAIL", "RITES",
                                        "IRCTC", "RKFORGE", "CONCOR")}
SYMBOL_THEME.update({s: "Defence" for s in ("MAZDOCK", "COCHINSHIP", "GRSE", "BEML", "BDL", "HAL", "BEL", "DATAPATTNS",
                                            "PARAS", "ZENTEC", "ASTRAMICRO", "SOLARINDS", "MIDHANI")})
SYMBOL_THEME.update({s: "Exchanges & Depositories" for s in ("BSE", "CDSL", "MCX", "IEX", "CAMS", "KFINTECH", "NSDL")})
SYMBOL_THEME.update({s: "Wind & Solar Equipment" for s in ("SUZLON", "INOXWIND", "WAAREEENER", "PREMIERENE")})


def theme(symbol, industry, name=""):
    if symbol in SYMBOL_THEME:
        return SYMBOL_THEME[symbol]
    if isinstance(industry, str) and industry.startswith("Banks"):
        if symbol in PSU_BANKS:
            return "PSU Banks"
        return "Small Finance Banks" if "small finance" in str(name).lower() else "Private Banks"
    if not isinstance(industry, str) or not industry:
        return "Unclassified"
    return RENAME.get(industry, industry)
