"""Get GSP boundary data from eso """
from typing import List, Optional, Union

import structlog
from fastapi import APIRouter, Depends, Request, Security
from fastapi_auth0 import Auth0User
from nowcasting_datamodel.models import (
    Forecast,
    ForecastValue,
    GSPYield,
    LocationWithGSPYields,
    ManyForecasts,
)
from sqlalchemy.orm.session import Session

from auth_utils import get_auth_implicit_scheme, get_user
from cache import cache_response
from database import (
    get_forecasts_for_a_specific_gsp_from_database,
    get_forecasts_from_database,
    get_latest_forecast_values_for_a_specific_gsp_from_database,
    get_session,
    get_truth_values_for_a_specific_gsp_from_database,
    get_truth_values_for_all_gsps_from_database,
    save_api_call_to_db,
)

logger = structlog.stdlib.get_logger()


router = APIRouter()
NationalYield = GSPYield


# corresponds to route /v0/solar/GB/gsp/forecast/all
@router.get(
    "/forecast/all",
    response_model=ManyForecasts,
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_all_available_forecasts(
    request: Request,
    historic: Optional[bool] = True,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> ManyForecasts:
    """### Get the latest information for all available forecasts for all GSPs

    The return object contains a forecast object with system details and forecast values for all GSPs.

    This request may take a longer time to load because a lot of data is being pulled from the
    database.

    #### Parameters
    - **historic**: boolean value set to True returns the forecasts of yesterday along with today's
    forecasts for all GSPs

    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(f"Get forecasts for all gsps. The option is {historic=} for user {user}")

    forecasts = get_forecasts_from_database(session=session, historic=historic)

    forecasts.normalize()

    return forecasts


@router.get(
    "/forecast/{gsp_id}",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
    include_in_schema=False,
)
@cache_response
def get_forecasts_for_a_specific_gsp_old_route(
    request: Request,
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> Union[Forecast, List[ForecastValue]]:
    return get_forecasts_for_a_specific_gsp(
        request=request,
        gsp_id=gsp_id,
        session=session,
        forecast_horizon_minutes=forecast_horizon_minutes,
        user=user,
    )


@router.get(
    "/{gsp_id}/forecast",
    response_model=Union[Forecast, List[ForecastValue]],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_forecasts_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    session: Session = Depends(get_session),
    forecast_horizon_minutes: Optional[int] = None,
    user: Auth0User = Security(get_user()),
) -> Union[Forecast, List[ForecastValue]]:
    """### Get recent forecast values for a specific GSP

    Returns an 8-hour solar generation forecast for a specific GSP with option
    to change the forecast horizon.

    The _forecast_horizon_minutes_ parameter allows
    a user to query for a forecast closer than 8 hours to the target time.

    For example, if the target time is 10am today, the forecast made at 2am
    today is the 8-hour forecast for 10am, and the forecast made at 6am for
    10am today is the 4-hour forecast for 10am.

    #### Parameters
    - **gsp_id**: **gsp_id** of the desired forecast
    - **forecast_horizon_minutes**: optional forecast horizon in minutes (ex. 60
    returns the latest forecast made 60 minutes before the target time)
    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(f"Get forecasts for gsp id {gsp_id} forecast of forecast with only values.")
    logger.info(f"This is for user {user}")

    forecast_values_for_specific_gsp = get_latest_forecast_values_for_a_specific_gsp_from_database(
        session=session,
        gsp_id=gsp_id,
        forecast_horizon_minutes=forecast_horizon_minutes,
    )

    logger.debug("Got forecast values for a specific gsp.")

    return forecast_values_for_specific_gsp


# corresponds to API route /v0/solar/GB/gsp/pvlive/all
@router.get(
    "/pvlive/all",
    response_model=List[LocationWithGSPYields],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_truths_for_all_gsps(
    request: Request,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[LocationWithGSPYields]:
    """### Get PV_Live values for all GSPs for yesterday and/or today

    The return object is a series of real-time PV generation estimates or
    truth values from PV_Live for all GSPs.

    Setting the _regime_ parameter to _day-after_ includes
    the previous day's truth values for the GSPs. The default is _in-day__.

    If regime is not specified, the most up-to-date GSP yield is returned.

    #### Parameters
    - **regime**: can choose __in-day__ or __day-after__
    """
    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(f"Get PV Live estimates values for all gsp id and regime {regime} for user {user}")

    return get_truth_values_for_all_gsps_from_database(session=session, regime=regime)


@router.get(
    "/pvlive/{gsp_id}",
    response_model=List[GSPYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
    include_in_schema=False,
)
@cache_response
def get_truths_for_a_specific_gsp_old_route(
    request: Request,
    gsp_id: int,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[GSPYield]:
    return get_truths_for_a_specific_gsp(
        request=request,
        gsp_id=gsp_id,
        regime=regime,
        session=session,
        user=user,
    )


# corresponds to API route /v0/solar/GB/gsp/pvlive/{gsp_id}
@router.get(
    "/{gsp_id}/pvlive",
    response_model=List[GSPYield],
    dependencies=[Depends(get_auth_implicit_scheme())],
)
@cache_response
def get_truths_for_a_specific_gsp(
    request: Request,
    gsp_id: int,
    regime: Optional[str] = None,
    session: Session = Depends(get_session),
    user: Auth0User = Security(get_user()),
) -> List[GSPYield]:
    """### Get PV_Live values for a specific GSP for yesterday and today

    The return object is a series of real-time solar energy generation
    from PV_Live for a single GSP.

    Setting the __regime__ parameter to __day-after__ includes
    the previous day's truth values for the GSPs. The default is __in-day__.

    If regime is not specified, the most up-to-date GSP yield is returned.

    #### Parameters
    - **gsp_id**: gsp_id of the requested forecast
    - **regime**: can choose __in-day__ or __day-after__
    """

    save_api_call_to_db(session=session, user=user, request=request)

    logger.info(
        f"Get PV Live estimates values for gsp id {gsp_id} " f"and regime {regime} for user {user}"
    )

    return get_truth_values_for_a_specific_gsp_from_database(
        session=session, gsp_id=gsp_id, regime=regime
    )