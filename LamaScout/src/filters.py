from typing import Optional
import pandas as pd


def normalize_filter_value(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    value = str(value).strip().lower()
    return value if value else None


def apply_filters(
    df: pd.DataFrame,
    genre: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    country: Optional[str] = None,
    age_group: Optional[str] = None,
    agt_stage: Optional[str] = None,
    tier: Optional[str] = None,
    label_interest: Optional[str] = None,
    not_signed: Optional[bool] = None,
    today: Optional[str] = None,
    tomorrow: Optional[str] = None,
    scope: Optional[str] = None,
) -> pd.DataFrame:
    if scope:
        normalized_scope = normalize_filter_value(scope)
        if normalized_scope == "usa":
            country = "usa"

    genre = genre or today or tomorrow
    genre = normalize_filter_value(genre)
    city = normalize_filter_value(city)
    state = normalize_filter_value(state)
    country = normalize_filter_value(country)
    age_group = normalize_filter_value(age_group)
    agt_stage = normalize_filter_value(agt_stage)
    tier = normalize_filter_value(tier)
    label_interest = normalize_filter_value(label_interest)

    filters = []
    if genre is not None:
        filters.append(df["genre"].astype(str).str.lower() == genre)
    if city is not None:
        filters.append(df["city"].astype(str).str.lower() == city)
    if state is not None:
        filters.append(df["state"].astype(str).str.lower() == state)
    if country is not None:
        filters.append(df["country"].astype(str).str.lower() == country)
    if age_group is not None:
        filters.append(df["age_group"].astype(str).str.lower() == age_group)
    if agt_stage is not None:
        filters.append(df["agt_stage"].astype(str).str.lower() == agt_stage)
    if tier is not None:
        filters.append(df["tier"].astype(str).str.lower() == tier)
    if label_interest is not None:
        filters.append(df["label_interest"].astype(str).str.lower() == label_interest)
    if not_signed is not None:
        unsigned_series = df["unsigned_prospect"] if "unsigned_prospect" in df.columns else pd.Series(False, index=df.index)
        if not_signed:
            filters.append(unsigned_series == True)
        else:
            filters.append(unsigned_series == False)

    if not filters:
        return df

    mask = filters[0]
    for extra in filters[1:]:
        mask = mask & extra
    return df[mask].copy()


def top_n_for_field(df: pd.DataFrame, field: str, value: str, top_n: int = 10) -> pd.DataFrame:
    if field not in df.columns:
        return pd.DataFrame()
    matches = df[df[field].astype(str).str.lower() == str(value).strip().lower()].copy()
    if matches.empty:
        return pd.DataFrame()
    return matches.sort_values(["champion_score", "followers_current_total"], ascending=[False, False]).head(top_n)
