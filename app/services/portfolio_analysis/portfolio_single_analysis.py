import io
import logging
import numpy as np
import pandas as pd

PROFILE_SHEET = "Profil Investisseur"
ESG_DATA_SHEET = "SOPIAD - ESG Data"
PORTFOLIOS_SHEET = "SOPIAD Portfolios"
ALLOCATION_SHEET = "Product - Market Data"
FINANCIAL_DATA_SHEET = "SOPIAD - Financial Data"
RISK_MAPPING_SHEET = "Risk mapping"


class PortfolioAnalysis:
    def __init__(self, excel_file: io.BytesIO, portfolio_weights: dict) -> None:
        self._load_data(excel_file)
        self.portfolio_weights = portfolio_weights

    def _load_data(self, excel_stream: io.BytesIO):
        excel_file = pd.ExcelFile(excel_stream)

        self.profils = pd.read_excel(excel_file, sheet_name=PROFILE_SHEET)
        self.product_ESG_data = pd.read_excel(excel_file, sheet_name=ESG_DATA_SHEET)
        self.portfolios = pd.read_excel(excel_file, sheet_name=PORTFOLIOS_SHEET)
        self.product_allocation = pd.read_excel(excel_file, sheet_name=ALLOCATION_SHEET)
        self.financial_data = pd.read_excel(
            excel_file, sheet_name=FINANCIAL_DATA_SHEET, header=[1]
        )
        self.financial_data = self.financial_data.drop(
            self.financial_data.index[0]
        )  # Drop the first row
        self.financial_data = self.financial_data.dropna(subset=["asset_name"])
        self.risk_mapping = pd.read_excel(excel_file, sheet_name=RISK_MAPPING_SHEET)

    def _build_profile_documentation_part(self, profile, product_ESG_data):
        full_profile_doc = "## Profil Investisseur \n"
        fields = [
            "Nom ",
            "Prénom",
            "Risk profile name",
            "Min_SFDR",
            "Min_Taxonomie ",
            "Portfolio_Alignment",
        ]

        # Add profile fields to the document
        for field in fields:
            if field in ["Min_SFDR", "Min_Taxonomie ", "Portfolio_Alignment"]:
                full_profile_doc += f"{field}: {profile[field]:.0%} \n"
            else:
                full_profile_doc += f"{field}: {profile[field]} \n"

        # Add Principal Adverse Impact (PAI) to the document
        # full_profile_doc += "Principal Adverse Impact (PAI) sélectionnés:\n"
        PAI_list = [int(i) for i in profile["PAI"].split(";")]
        all_pais = [
            col for PAI in PAI_list 
            for col in product_ESG_data.columns 
            if col.startswith(f"PAI {PAI} -")
            ]
        # full_profile_doc += "".join(f"   - {col}\n" for col in all_pais)

        # all_sdgs = []
        # for PAI in PAI_list:
        #     for col in product_ESG_data.columns:
        #         if col.startswith(f"PAI {PAI} -"):
        #             all_pais.append(col)
        #             full_profile_doc += f"   - {col}\n"

        # Add Sustainable Development Goals (SDGs) to the document
        # full_profile_doc += "Sustainable Development Goals (SDGs) sélectionnés:\n"
        SDG_list = [int(i) for i in profile["ODD"].split(",")]
        all_sdgs = [
            col for SDG in SDG_list
            for col in product_ESG_data.columns
            if col.startswith(f"{SDG:02d} -")
            ]
        
        # full_profile_doc += "".join(f"   - {col}\n" for col in all_sdgs)

        return full_profile_doc, all_pais, all_sdgs

    def _build_risk_profile(self, risk_profile_id, risk_mapping_df):
        full_risk_profile_doc = "## Profil de risque dynamique \n"
        row = risk_mapping_df[risk_mapping_df["risk_profile_ID"] == risk_profile_id].iloc[0]
        fields = ["Equity", "Bonds", "Cash", "SRI"]
        
        for field in fields:
            field_min = row[f"{field}_Min"]
            field_max = row[f"{field}_Max"]
            if field != "SRI":
                field_min = f"{field_min:.0%}"
                field_max = f"{field_max:.0%}"
            full_risk_profile_doc += f"{field}: between {field_min} and {field_max}\n"
        
        return full_risk_profile_doc


    def _generate_portfolio_string(self, profile):
        current_portfolio = self.portfolio_weights.get("Current", {})
        simulated_portfolio = self.portfolio_weights.get("Simulated", {})

        def format_portfolio(portfolio, title):
            portfolio_str = f"{title} – {len(portfolio)} funds:\n"
            portfolio_str += "".join(
                f"- {product_name}: {weight:.0%}\n"
                for product_name, weight in portfolio.items()
            )
            return portfolio_str
        current_str = format_portfolio(current_portfolio, "Current portfolio composition")
        simulated_str = format_portfolio(simulated_portfolio, "Simulated portfolio")

        # TODO: moet nog verbeterd worden
        comparison_red_str = "-> Simulated portfolio reduces exposure to:\n"
        comparison_inc_str = "Simulated portfolio increases exposure to:\n"

        def compare_portfolios(current, simulated):
            red_str, inc_str = "", ""
            for product_name, current_weight in current.items():
                simulated_weight = simulated.get(product_name, 0)
                diff = simulated_weight - current_weight
                if diff < 0:
                    red_str += f"{product_name} ({diff:.0%}), "
                elif diff > 0:
                    inc_str += f"{product_name} (+{diff:.0%}), "
            for product_name, simulated_weight in simulated.items():
                if product_name not in current:
                    inc_str += f"{product_name} (+{simulated_weight:.0%}), "
            return red_str.rstrip(", "), inc_str.rstrip(", ")

        comparison_red_str, comparison_inc_str = compare_portfolios(
            current_portfolio, simulated_portfolio
        )

        full_name = f"{profile['Prénom']} {profile['Nom ']}"

        result = (
            f"## {full_name} Portfolio \n"
            f"{current_str}\n"
            f"{simulated_str}\n"
            f"{comparison_red_str}\n"
            f"{comparison_inc_str}"
        )
        return result

    def _generate_portfolio(self, profile):
        current_portfolio = self.portfolio_weights.get("Current", {})
        def format_portfolio(portfolio, title):
            portfolio_str = f"{title} – {len(portfolio)} funds:\n"
            portfolio_str += "".join(
                f"- {product_name}: {weight:.0%}\n"
                for product_name, weight in portfolio.items()
            )
            return portfolio_str
        current_str = format_portfolio(current_portfolio, "Current portfolio composition")
        full_name = f"{profile['Prénom']} {profile['Nom ']}"
        result = (
            f"## {full_name} Portfolio \n"
            f"{current_str}"
        )
        return result



    def _generate_geographical_allocations(self, product_allocation):
        current_portfolio = self.portfolio_weights.get("Current", {})        
        relevant_portfolios = set(
            list(current_portfolio.keys())
        )

        european_country_list = [
            "Suede",
            "Hollande",
            "France ",
            "Allemagne",
            "Espagne",
            "Italie",
            "Angleterre",
            "Finlande",
            "Luxembourg",
            "Belgique",
        ]
        non_european_country_list = ["Etat Unis", "Canada ", "Chine"]

        full_string = "## Geographical allocations \n"
        geo_allocation = {}

        # Function to format allocations as a string
        def add_allocations(row, title=None):
            allocation = {}
            result_string = f"{title}\n" if title else f"{row['product_name ']}\n"
            total_europe = sum(row[country] for country in european_country_list)
            result_string += f"- Europe: {total_europe:.0%}\n"
            allocation['Europe'] = total_europe
            for country in non_european_country_list:
                if row[country]:
                    result_string += f"- {country}: {row[country]:.0%}\n"
                    allocation[country] = row[country]
            geo_allocation[row['product_name ']] = allocation
            return result_string
        
        def calculate_portfolio_geo_allocation(portfolio_weights):
            geo_allocation_current_sim = {}
            for fund, weight in portfolio_weights.items():
                for region, region_weight in geo_allocation[fund].items():
                    geo_allocation_current_sim[region] = geo_allocation_current_sim.get(region, 0) + weight * float(region_weight)
            return geo_allocation_current_sim
        
        def format_allocations(allocation, title=None):
            result_string = f"{title}\n" if title else ""
            for region, weight in allocation.items():
                result_string += f"- {region}: {weight:.0%}\n"
            return result_string
        
        for _, row in product_allocation.iterrows():
            if row["product_name "] in relevant_portfolios:
                full_string += add_allocations(row)
            elif row["product_code"] == "Current Boost ":
                full_string += format_allocations(
                    calculate_portfolio_geo_allocation(current_portfolio),
                    "Current portfolio geographical allocation:"
                )

        countries_total_current = calculate_portfolio_geo_allocation(current_portfolio)
        
        # TODO: text nog toevoegen
        return full_string

    def _generate_sector_allocations(self, product_allocation):
        current_portfolio = self.portfolio_weights.get("Current", {})
        relevant_portfolios = set(
            list(current_portfolio.keys())
        )

        sector_list = [
            "Automobile",
            "Santé",
            "Technologie",
            "Financier",
            "Energie",
            "Industrie",
            "Télécom",
            "Immobilier",
        ]

        full_string = "## Sectors allocations \n"
        sector_allocation = {}

        def add_allocations(row, title=None):
            allocation = {}
            result_string = f"{title}\n" if title else f"{row['product_name ']}\n"
            for sector in sector_list:
                weight = row.get(sector, 0)
                result_string += f"- {sector}: {weight:.0%}\n"
                allocation[sector] = weight
            sector_allocation[row['product_name ']] = allocation
            return result_string
        
        def calculate_portfolio_allocation(portfolio_weights):
            portfolio_allocation = {}
            for fund, weight in portfolio_weights.items():
                for sector, sector_weight in sector_allocation[fund].items():
                    portfolio_allocation[sector] = portfolio_allocation.get(sector, 0) + weight * (sector_weight)
            return portfolio_allocation
        
        # Function to format allocations as a string
        def format_allocations(allocation, title=None):
            result_string = f"{title}\n" if title else ""
            for sector, weight in allocation.items():
                result_string += f"- {sector}: {weight:.0%}\n"
            return result_string
        
        for _, row in product_allocation.iterrows():
            if row["product_name "] in relevant_portfolios:
                full_string += add_allocations(row)
            elif row["product_code"] == "Current Boost ":
                full_string += format_allocations(
                    calculate_portfolio_allocation(current_portfolio),
                    "Current portfolio sector allocation:"
                )
        # TODO: text nog toevoegen
        return full_string

    def _generate_asset_allocations(self, product_allocation):
        current_portfolio = self.portfolio_weights.get("Current", {})
        relevant_portfolios = set(current_portfolio.keys())

        sector_list = ["bonds", "equities", "Funds", "Other"]

        full_string = "## Asset allocation \n"

        befo_allocation = {}

        def add_allocations(row, title=None):
            allocation = {}
            result_string = f"{title}\n" if title else f"{row['product_name ']}\n"
            for sector in sector_list:
                weight = row.get(f"%_{sector}_current", 0)
                result_string += f"- {sector}: {weight:.0%}\n"
                allocation[sector] = weight
            befo_allocation[row['product_name ']] = allocation
            return result_string
        
        def calculate_befo_allocation(portfolio_weights):
            portfolio_allocation = {}
            for fund, weight in portfolio_weights.items():
                for befo, befo_weight in befo_allocation[fund].items():
                    portfolio_allocation[befo] = portfolio_allocation.get(befo, 0) + weight * befo_weight
            return portfolio_allocation
        
        # Function to format allocations as a string
        def format_allocations(allocation, title=None):
            result_string = f"{title}\n" if title else ""
            for befo, weight in allocation.items():
                result_string += f"- {befo}: {weight:.0%}\n"
            return result_string

        for _, row in product_allocation.iterrows():
            if row["product_name "] in relevant_portfolios:
                full_string += add_allocations(row)
            elif row["product_code"] == "Current Boost ":
                full_string += format_allocations(
                    calculate_befo_allocation(current_portfolio),
                    "Current portfolio asset allocation:"
                )
        # TODO: text nog toevoegen
        return full_string

    def _generate_PAI(self, all_pais, product_ESG_data):
        product_ESG_data[["Date", "asset_code", "asset_name"]] = product_ESG_data[
            ["Date", "asset_code", "asset_name"]
        ].fillna(value="")

        product_ESG_data['Date'] = pd.to_datetime(product_ESG_data['Date'], errors='coerce')
        product_ESG_data = product_ESG_data.sort_values(by='Date', ascending=False)

        current_portfolio = self.portfolio_weights.get("Current", {})
        full_string = "## PAI sélectionnés:\n"

        # def get_product_selected_pai(data, colum):


        def get_values(data, column, current_products, portfolio):
            value = sum(data[data["asset_name"] == product][column].iloc[0] * portfolio[product] for product in current_products)
            return value

        for pai in all_pais:
            full_string += f"-  {pai}\n"
            current_value = get_values(product_ESG_data, pai, list(current_portfolio.keys()), portfolio=
            current_portfolio)
            benchmark_value = product_ESG_data[product_ESG_data["asset_name"] == "BENCHMARK MSCI ESG"][pai].iloc[0]
            
            full_string += (
                f"     o Current portfolio : {current_value:.2f} – "
                f"Benchmark: {benchmark_value:.2f}\n"
            )
        
        # TODO: add explanation text
        return full_string

    def _generate_SDG(self, all_sdgs, product_ESG_data):
        product_ESG_data[["Date", "asset_code", "asset_name"]] = product_ESG_data[
            ["Date", "asset_code", "asset_name"]
        ].fillna(value="")

        current_portfolio = self.portfolio_weights.get("Current", {})
        full_string = "## Sustainable Development Goals (SDGs) sélectionnés:\n"
        
        def get_values(data, column, current_products, portfolio):
            value = sum(data[data["asset_name"] == product][column].iloc[0] * portfolio[product] for product in current_products)
            return value
        
        for sdg in all_sdgs:
            full_string += f"-  {sdg}\n"
            current_value = get_values(product_ESG_data, sdg, list(current_portfolio.keys()), portfolio=current_portfolio)
            benchmark_value = product_ESG_data[product_ESG_data["asset_name"] == "BENCHMARK MSCI ESG"][sdg].iloc[0]
            full_string += (
            f"     o Current portfolio : {current_value:.2%} – "
            f"Benchmark: {benchmark_value:.2%}\n"
            )

        # TODO: add explanation text
        return full_string
    
    def _generate_safir(self, product_ESG_data):
        full_string="## SAFIR:\n"
        port_weights = self.portfolio_weights["Current"]
        av_safir, av_esg_safir=0,0
        for key, value in port_weights.items():
            saf1=product_ESG_data[product_ESG_data["asset_name"] == key]["SAFIR_suitability"].iloc[0]
            saf2=product_ESG_data[product_ESG_data["asset_name"] == key]["SAFIR_ESG_impact"].iloc[0]
            av_safir += (
                product_ESG_data[product_ESG_data["asset_name"] == key][
                    "SAFIR_suitability"
                ].iloc[0]
                * value )
            av_esg_safir += (
                product_ESG_data[product_ESG_data["asset_name"] == key][
                    "SAFIR_ESG_impact"
                ].iloc[0]
                * value )
            full_string += (
            f"{key}\n"
            f"     o SAFIR suitability : {saf1}\n"
            f"     o SAFIR ESG impact: {saf2}\n")
        full_string += (
            f"Current portfolio asset allocation:\n"
            f"     o SAFIR suitability : {av_safir:.2}\n"
            f"     o SAFIR ESG impact: {av_esg_safir:.2}\n"
            )
        return full_string

    def _get_portfolio_weights(self, portfolios):
        relevant_portfolios = {}
        current_boost = portfolios[portfolios["portfolio_code"] == "CURRENT BOOST"]
        current_portfolio = {
            j["Product_name"]: j["weight"] for _, j in current_boost.iterrows()
        }
        relevant_portfolios["Current"] = current_portfolio

        simulated_boost = portfolios[portfolios["portfolio_code"] == "SIM BOOST"]
        simulated_portfolio = {
            j["Product_name"]: j["weight"] for _, j in simulated_boost.iterrows()
        }
        relevant_portfolios["Simulated"] = simulated_portfolio
        logging.info(relevant_portfolios)

        return relevant_portfolios
    
    def _generate_taxonomy(self, product_ESG_data, profil):
        full_string = "## Taxonomy \n"
        portfolio_weights = self.portfolio_weights
        required_taxonomy = profil["Min_Taxonomie "]
        port_weights = portfolio_weights["Current"]
        total_taxonomy = 0
        for key, value in port_weights.items():
            total_taxonomy += (
                product_ESG_data[product_ESG_data["asset_name"] == key][
                    "taxonomy_alignment"
                ].iloc[0]
                * value
            )

        full_string += f"portfolio: {total_taxonomy:.2%}\n"

        if total_taxonomy < required_taxonomy:
            full_string += f"taxonomy of the portfolio is below the required threshold of {required_taxonomy:.2%}\n"
        elif total_taxonomy > required_taxonomy:
            full_string += f"taxonomy of the portfolio is above the required threshold of {required_taxonomy:.2%}\n"
        else:
            full_string += (
                f"taxonomy of the portfolio matches the required threshold\n"
            )
        return full_string

    def _generate_sfdr(self, product_ESG_data, profil):
        full_string = "## SFDR \n"
        portfolio_weights = self.portfolio_weights
        required_taxonomy = profil["Min_SFDR"]
        port_weights = portfolio_weights["Current"]
        total_sfdr = 0
        for key, value in port_weights.items():
            total_sfdr += (
                product_ESG_data[product_ESG_data["asset_name"] == key][
                    "sfdr_alignment"
                ].iloc[0]
                * value
            )
        full_string += f"portfolio: {total_sfdr:.2%}\n"

        if total_sfdr < required_taxonomy:
            full_string += f"SFDR of the portfolio is below the required threshold of {required_taxonomy:.2%}\n"
        elif total_sfdr > required_taxonomy:
            full_string += f"SFDR of the portfolio is above the required threshold of {required_taxonomy:.2%}\n"
        else:
            full_string += (
                f"SFDR of the portfolio matches the required threshold\n"
            )
        return full_string

    def _calculate_yearly_performance(self, portfolio_dict, financial_data):
        last_year_financial_data = financial_data.iloc[-12:]
        totals_full_period = []
        for i, j in last_year_financial_data.iterrows():
            total_current = 0
            for key, value in portfolio_dict.items():
                total_current += j[key] * value
            totals_full_period.append(total_current + 1)

        full_year_performance = np.prod(totals_full_period) - 1
        return full_year_performance

    def _generate_yearly_performance_string(self, portfolios, financial_data):
        relevant_portfolios = self.portfolio_weights
        relevant_portfolios["Benchmark"] = {"MSCI ESG": 1}
        full_string = "## Yearly Financial performance \n"
        for key, value in relevant_portfolios.items():
            full_string += f"{key} portfolio: {self._calculate_yearly_performance(value, financial_data):.2%}\n"
        return full_string

    def generate_data_port(self):
        profile = self.profils.iloc[0]
        profile_doc, all_pais, all_sdgs = self._build_profile_documentation_part(
            profile, self.product_ESG_data
        )

        portfolio_sections = [
            "# PORTFOLIO DATA",
            profile_doc,
            self._build_risk_profile(profile["Risk profile id"], self.risk_mapping),
            self._generate_portfolio(profile),
            self._generate_geographical_allocations(
                self.product_allocation
            ),
            self._generate_sector_allocations(
                self.product_allocation
            ),
            self._generate_asset_allocations(
                self.product_allocation
            ),
            self._generate_safir(self.product_ESG_data),
            self._generate_SDG(all_sdgs, self.product_ESG_data),
            self._generate_PAI(all_pais, self.product_ESG_data),
            self._generate_taxonomy(
                self.product_ESG_data, profile
            ),
            self._generate_sfdr(self.product_ESG_data, profile),
            self._generate_yearly_performance_string(
                self.portfolios, self.financial_data
            ),
        ]
        #print("making the data string!")
        return "\n\n".join(portfolio_sections)+"\n\n"


    def get_risk_profile(self) -> str:
        profile = self.profils.iloc[0]
        return self._build_risk_profile(profile["Risk profile id"], self.risk_mapping)
    
    def get_client_name(self):
        profile = self.profils.iloc[0]
        return profile['Nom ']
    
    def get_sector(self) -> str:
        return self._generate_sector_allocations(self.product_allocation)
    
    def get_geograph(self) -> str:
        return self._generate_geographical_allocations(self.product_allocation)
    
    def get_assets(self) -> str:
        return self._generate_asset_allocations(self.product_allocation)
    
    def get_safir(self) -> str:
        return self._generate_safir(self.product_ESG_data)
    
    def get_SDG(self) -> str:
        profile = self.profils.iloc[0]
        profile_doc, all_pais, all_sdgs = self._build_profile_documentation_part(
            profile, self.product_ESG_data)
        return self._generate_SDG(all_sdgs, self.product_ESG_data)
    
    def get_pais(self) -> str:
        profile = self.profils.iloc[0]
        profile_doc, all_pais, all_sdgs = self._build_profile_documentation_part(
            profile, self.product_ESG_data)
        return self._generate_PAI(all_pais, self.product_ESG_data)
    
    def get_taxonomy(self) -> str:
        profile = self.profils.iloc[0]
        return self._generate_taxonomy(self.product_ESG_data, profile)
    
    def get_sfdr(self) -> str:
        profile = self.profils.iloc[0]
        return self._generate_sfdr(self.product_ESG_data, profile)
    
    def get_performance(self) -> str:
        return self._generate_yearly_performance_string(self.portfolios, self.financial_data)