""" local API to manage system, units and zones """ 

import re, sys, os
import logging as log
import asyncio

from homeassistant.helpers.entity import DeviceInfo
from ..const import DOMAIN

from . import const
from .operations import Operations, ModbusConnexionError

_LOGGER = log.getLogger(__name__)

class Area:
    ''' koolnova Area class '''

    def __init__(self,
                    name:str = "",
                    id_zone:int = 0,
                    state:const.ZoneState = const.ZoneState.STATE_OFF,
                    register:const.ZoneRegister = const.ZoneRegister.REGISTER_OFF,
                    fan_mode:const.ZoneFanMode = const.ZoneFanMode.FAN_OFF,
                    clim_mode:const.ZoneClimMode = const.ZoneClimMode.OFF,
                    real_temp:float = 0,
                    order_temp:float = 0
                ) -> None:
        ''' Class constructor '''
        self._name = name
        self._id = id_zone
        self._state = state
        self._register = register
        self._fan_mode = fan_mode
        self._clim_mode = clim_mode
        self._real_temp = real_temp
        self._order_temp = order_temp

    @property
    def name(self) -> str:
        ''' Get area name '''
        return self._name

    @name.setter
    def name(self, name:str) -> None:
        ''' Set area name '''
        if not isinstance(name, str):
            raise AssertionError('Input variable must be a string')
        self._name = name

    @property
    def id_zone(self) -> int:
        ''' Get Zone Id '''
        return self._id

    @property
    def state(self) -> const.ZoneState:
        ''' Get state '''
        return self._state

    @state.setter
    def state(self, val:const.ZoneState) -> None:
        ''' Set state '''
        if not isinstance(val, const.ZoneState):
            raise AssertionError('Input variable must be Enum ZoneState')
        self._state = val

    @property
    def register(self) -> const.ZoneRegister:
        ''' Get register state '''
        return self._register

    @register.setter
    def register(self, val:const.ZoneRegister) -> None:
        ''' Set register state '''
        if not isinstance(val, const.ZoneRegister):
            raise AssertionError('Input variable must be Enum ZoneRegister')
        self._register = val

    @property
    def fan_mode(self) -> const.ZoneFanMode:
        ''' Get Fan Mode '''
        return self._fan_mode

    @fan_mode.setter
    def fan_mode(self, val:const.ZoneFanMode) -> None:
        ''' Set Fan Mode '''
        if not isinstance(val, const.ZoneFanMode):
            raise AssertionError('Input variable must be Enum ZoneFanMode')
        self._fan_mode = val

    @property
    def clim_mode(self) -> const.ZoneClimMode:
        ''' Get Clim Mode '''
        return self._clim_mode

    @clim_mode.setter
    def clim_mode(self, val:const.ZoneClimMode) -> None:
        ''' Set Clim Mode '''
        if not isinstance(val, const.ZoneClimMode):
            raise AssertionError('Input variable must be Enum ZoneClimMode')
        self._clim_mode = val

    @property
    def real_temp(self) -> float:
        ''' Get real temp '''
        return self._real_temp

    @real_temp.setter
    def real_temp(self, val:float) -> None:
        ''' Set Real Temp '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be Float')
        self._real_temp = val

    @property
    def order_temp(self) -> float:
        ''' Get order temp '''
        return self._order_temp

    @order_temp.setter
    def order_temp(self, val:float) -> None:
        ''' Set Order Temp '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be float')
        if val > const.MAX_TEMP_ORDER or val < const.MIN_TEMP_ORDER:
            raise OrderTempError('Order temp value must be between {} and {}'.format(const.MIN_TEMP_ORDER, const.MAX_TEMP_ORDER))
        self._order_temp = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('Zone(Name: {}, Id:{}, State:{}, Register:{}, Fan:{}, Clim:{}, Real Temp:{}, Order Temp:{})'.format(
                        self._name,
                        self._id, 
                        self._state,
                        self._register,
                        self._fan_mode,
                        self._clim_mode,
                        self._real_temp,
                        self._order_temp))

class Koolnova:
    ''' koolnova Device class '''

    def __init__(self,
                    name:str = "",
                    port:str = "",
                    addr:int = const.DEFAULT_ADDR,
                    baudrate:int = const.DEFAULT_BAUDRATE,
                    parity:str = const.DEFAULT_PARITY,
                    bytesize:int = const.DEFAULT_BYTESIZE,
                    stopbits:int = const.DEFAULT_STOPBITS,
                    timeout:int = 1) -> None:
        ''' Class constructor '''
        self._client = Operations(port=port,
                                    addr=addr,
                                    baudrate=baudrate,
                                    parity=parity,
                                    bytesize=bytesize,
                                    stopbits=stopbits,
                                    timeout=timeout)
        self._name = name
        self._global_mode = const.GlobalMode.COLD
        self._efficiency = const.Efficiency.LOWER_EFF
        self._sys_state = const.SysState.SYS_STATE_OFF 
        self._units = []
        self._areas = [] 

    def _area_defined(self, 
                        id_search:int = 0,
                    ) -> (bool, int):
        """ test if area id is defined """
        _areas_found = [idx for idx,x in enumerate(self._areas) if x.id_zone == id_search]
        _idx = 0
        if not _areas_found:
            _LOGGER.error("Area id ({}) not defined".format(id_search))
            return False, _idx
        elif len(_areas_found) > 1:
            _LOGGER.error("Multiple Area with same id ({})".format(id_search))
            return False, _idx
        else:
            _LOGGER.debug("idx found: {}".format(_idx))
            _idx  = _areas_found[0]
        return True, _idx

    async def update(self) -> bool:
        ''' update values from modbus '''
        _LOGGER.debug("Retreive system status ...")
        ret, self._sys_state = await self._client.system_status()
        if not ret:
            _LOGGER.error("Error retreiving system status")
            self._sys_state = const.SysState.SYS_STATE_OFF

        _LOGGER.debug("Retreive global mode ...")
        ret, self._global_mode = await self._client.global_mode()
        if not ret:
            _LOGGER.error("Error retreiving global mode")
            self._global_mode = const.GlobalMode.COLD

        _LOGGER.debug("Retreive efficiency ...")
        ret, self._efficiency = await self._client.efficiency()
        if not ret:
            _LOGGER.error("Error retreiving efficiency")
            self._efficiency = const.Efficiency.LOWER_EFF
        
        #await asyncio.sleep(0.1)

        #_LOGGER.debug("Retreive units ...")
        #for idx in range(1, const.NUM_OF_ENGINES + 1):
        #    _LOGGER.debug("Unit id: {}".format(idx))
        #    unit = Unit(unit_id = idx)
        #    ret, unit.flow_engine = await self._client.flow_engine(unit_id = idx)
        #    ret, unit.flow_state = await self._client.flow_state_engine(unit_id = idx)
        #    ret, unit.order_temp = await self._client.order_temp_engine(unit_id = idx)
        #    self._units.append(unit)
        #    await asyncio.sleep(0.1)
        
        return True

    async def connect(self) -> bool:
        ''' connect to the modbus serial server '''
        ret = True
        await self._client.connect()
        if not self.connected():
            ret = False
            raise ClientNotConnectedError("Client Modbus connexion error")

        #_LOGGER.info("Update system values")
        #ret = await self.update()

        return ret

    def connected(self) -> bool:
        ''' get modbus client status '''
        return self._client.connected

    def disconnect(self) -> None:
        ''' close the underlying socket connection '''
        self._client.disconnect()

    async def discover_zones(self) -> None:
        ''' Set all registered zones for system '''
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')
        zones_lst = await self._client.discover_registered_zones()
        for zone in zones_lst:
            self._areas.append(Area(name = zone['name'],
                                    id_zone = zone['id'],
                                    state = zone['state'],
                                    register = zone['register'],
                                    fan_mode = zone['fan'],
                                    clim_mode = zone['clim'],
                                    real_temp = zone['real_temp'],
                                    order_temp = zone['order_temp']
                                    ))
        return

    async def add_manual_registered_zone(self,
                                            name:str = "",
                                            id_zone:int = 0) -> bool:
        ''' Add zone manually to koolnova System '''
        if not self._client.connected:
            raise ModbusConnexionError('Client Modbus not connected')

        ret, zone_dict = await self._client.zone_registered(zone_id = id_zone)
        if not ret:
            _LOGGER.error("Zone with ID: {} is not registered".format(id_zone))
            return False
        for zone in self._areas:
            if id_zone == zone.id_zone:
                _LOGGER.error('Zone registered with ID: {} is already saved')
                return False
        
        self._areas.append(Area(name = name,
                                id_zone = id_zone,
                                state = zone_dict['state'],
                                register = zone_dict['register'],
                                fan_mode = zone_dict['fan'],
                                clim_mode = zone_dict['clim'],
                                real_temp = zone_dict['real_temp'],
                                order_temp = zone_dict['order_temp']
                                ))
        _LOGGER.debug("Zones registered: {}".format(self._areas))
        return True

    @property
    def areas(self) -> list:
        ''' get areas '''
        return self._areas

    def get_area(self, zone_id:int = 0) -> Area:
        ''' get specific area '''
        return self._areas[zone_id - 1]

    async def update_area(self, zone_id:int = 0) -> bool:
        """ update area """
        ret, infos = await self._client.zone_registered(zone_id = zone_id)
        if not ret:
            _LOGGER.error("Error retreiving area ({}) values".format(zone_id))
            return ret, None
        for idx, area in enumerate(self._areas):
                if area.id_zone == zone_id:
                    # update areas list value from modbus response
                    self._areas[idx].state = infos['state']
                    self._areas[idx].register = infos['register']
                    self._areas[idx].fan_mode = infos['fan']
                    self._areas[idx].clim_mode = infos['clim']
                    self._areas[idx].real_temp = infos['real_temp']
                    self._areas[idx].order_temp = infos['order_temp']
                    break
        return ret, self._areas[zone_id - 1]

    def get_units(self) -> list:
        ''' get units '''
        return self._units

    @property
    def device_info(self) -> DeviceInfo:
        """ Return a device description for device registry """
        return {
            "name": self._name,
            "manufacturer": "Koolnova",
            "identifiers": {(DOMAIN, "deadbeef")},
        }

    @property
    def name(self) -> str:
        ''' Get name '''
        return self._name

    @property
    def global_mode(self) -> const.GlobalMode:
        ''' Get Global Mode '''
        return self._global_mode

    async def set_global_mode(self,
                                val:const.GlobalMode,
                                ) -> None:
        ''' Set Global Mode '''
        _LOGGER.debug("set global mode : {}".format(val))
        if not isinstance(val, const.GlobalMode):
            raise AssertionError('Input variable must be Enum GlobalMode')
        ret = await self._client.set_global_mode(val)
        if not ret:
            raise UpdateValueError('Error writing to modbus updated value')
        self._global_mode = val

    @property
    def efficiency(self) -> const.Efficiency:
        ''' Get Efficiency '''
        return self._efficiency

    async def set_efficiency(self,
                                val:const.Efficiency,
                            ) -> None:
        ''' Set Efficiency '''
        _LOGGER.debug("set efficiency : {}".format(val))
        if not isinstance(val, const.Efficiency):
            raise AssertionError('Input variable must be Enum Efficiency')
        ret = await self._client.set_efficiency(val)
        if not ret:
            raise UpdateValueError('Error writing to modbus updated value')    
        self._efficiency = val

    @property
    def sys_state(self) -> const.SysState:
        ''' Get System State '''
        return self._sys_state

    async def set_sys_state(self,
                            val:const.SysState,
                            ) -> None:
        ''' Set System State '''
        if not isinstance(val, const.SysState):
            raise AssertionError('Input variable must be Enum SysState')
        ret = await self._client.set_system_status(val)
        if not ret:
            raise UpdateValueError('Error writing to modbus updated value') 
        self._sys_state = val

    async def get_area_temp(self,
                            zone_id:int,
                            ) -> float:
        """ get current temp of specific Area """
        ret, temp = await self._client.area_temp(id_zone = zone_id)
        if not ret:
            _LOGGER.error("Error reading temp for area with ID: {}".format(zone_id))
            return False
        for idx, area in enumerate(self._areas):
            if area.id_zone == zone_id:
                # update areas list value from modbus response
                self._areas[idx].real_temp = temp

        return temp

    async def set_area_target_temp(self,
                                    zone_id:int,
                                    temp:float,
                                    ) -> bool:
        """ set target temp of specific area """
        ret = await self._client.set_area_target_temp(zone_id = zone_id, val = temp)
        if not ret:
            _LOGGER.error("Error writing target temp for area with ID: {}".format(zone_id))
            return False
        for idx, area in enumerate(self._areas):
            if area.id_zone == zone_id:
                # update areas list value from modbus response
                self._areas[idx].order_temp = temp
        return True

    async def get_area_target_temp(self,
                                    zone_id:int,
                                    ) -> float:
        """ get target temp of specific area """
        ret, temp = await self._client.area_target_temp(id_zone = zone_id)
        if not ret:
            _LOGGER.error("Error reading target temp for area with ID: {}".format(zone_id))
            return 0.0
        for idx, area in enumerate(self._areas):
            if area.id_zone == zone_id:
                # update areas list value from modbus response
                self._areas[idx].order_temp = temp
        return temp

    async def set_area_clim_mode(self,
                                    zone_id:int, 
                                    mode:const.ZoneClimMode,
                                    ) -> bool:
        """ set climate mode for specific area """
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            return False

        if mode == const.ZoneClimMode.OFF:
            _LOGGER.debug("Set area state to OFF")
            ret = await self._client.set_area_state(id_zone = zone_id, val = const.ZoneState.STATE_OFF)
            if not ret:
                _LOGGER.error("Error writing area state for area with ID: {}".format(zone_id))
                return False
            self._areas[_idx].state = const.ZoneState.STATE_OFF
        else:
            if self._areas[_idx].state == const.ZoneState.STATE_OFF:
                _LOGGER.debug("Set area state to ON")
                # update area state
                ret = await self._client.set_area_state(id_zone = zone_id, val = const.ZoneState.STATE_ON)
                if not ret:
                    _LOGGER.error("Error writing area state for area with ID: {}".format(zone_id))
                    return False
            _LOGGER.debug("clim mode ? {}".format(mode))
            # update clim mode
            ret = await self._client.set_area_clim_mode(id_zone = zone_id, val = mode)
            if not ret:
                _LOGGER.error("Error writing climate mode for area with ID: {}".format(zone_id))
                return False
            self._areas[_idx].clim_mode = mode
        return True

    async def set_area_fan_mode(self,
                                zone_id:int, 
                                mode:const.ZoneFanMode,
                                ) -> bool:
        """ set fan mode for specific area """
        # test if area id is defined
        _ret, _idx = self._area_defined(id_search = zone_id)
        if not _ret:
            return False

        if self._areas[_idx].state == const.ZoneState.STATE_OFF:
            _LOGGER.warning("Area state is off, cannot change fan speed ...")
            return False
        else:
            _LOGGER.debug("fan mode ? {}".format(mode))
            # writing new value to modbus
            ret = await self._client.set_area_fan_mode(id_zone = zone_id, val = mode)
            if not ret:
                _LOGGER.error("Error writing fan mode for area with ID: {}".format(zone_id))
                return False
            # update fan mode in list for specific area
            self._areas[_idx].fan_mode = mode
        return True

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('System(Global Mode:{}, Efficiency:{}, State:{})'.format(
                        self._global_mode,
                        self._efficiency,
                        self._sys_state))

class Unit:
    ''' koolnova Unit class '''

    def __init__(self,
                    unit_id:int = 0,
                    flow_engine:int = 0,
                    flow_state:const.FlowEngine = const.FlowEngine.AUTO,
                    order_temp:float = 0
                ) -> None:
        ''' Constructor class '''
        self._unit_id = unit_id
        self._flow_engine = flow_engine
        self._flow_state = flow_state
        self._order_temp = order_temp

    @property
    def unit_id(self) -> int:
        ''' Get Unit ID '''
        return self._unit_id

    @unit_id.setter
    def unit_id(self, val:int) -> None:
        ''' Set Unit ID '''
        if not isinstance(val, int):
            raise AssertionError('Input variable must be Int')
        if val > const.NUM_OF_ENGINES:
            raise NumUnitError('Unit ID must be lower than {}'.format(const.NUM_OF_ENGINES))
        self._unit_id = val

    @property
    def flow_engine(self) -> int:
        ''' Get Flow Engine '''
        return self._flow_engine

    @flow_engine.setter
    def flow_engine(self, val:int) -> None:
        ''' Set Flow Engine '''
        if not isinstance(val, int):
            raise AssertionError('Input variable must be Int')
        if val > const.FLOW_ENGINE_VAL_MAX or val < const.FLOW_ENGINE_VAL_MIN:
            raise FlowEngineError('Flow Engine value ({}) must be between {} and {}'.format(val,
                                    const.FLOW_ENGINE_VAL_MIN,
                                    const.FLOW_ENGINE_VAL_MAX))
        self._flow_engine = val

    @property
    def flow_state(self) -> const.FlowEngine:
        ''' Get Flow State '''
        return self._flow_state

    @flow_state.setter
    def flow_state(self, val:const.FlowEngine) -> None:
        ''' Set Flow State '''
        if not isinstance(val, const.FlowEngine):
            raise AssertionError('Input variable must be Enum FlowEngine')
        self._flow_state = val

    @property
    def order_temp(self) -> float:
        ''' Get Order Temp '''
        return self._order_temp

    @order_temp.setter
    def order_temp(self, val:float = 0.0) -> None:
        ''' Set Flow Engine '''
        if not isinstance(val, float):
            raise AssertionError('Input variable must be Int')
        if val > 0 and (val > 30.0 or val < 15.0):
            raise OrderTempError('Flow Engine value ({}) must be between 15 and 30'.format(val))
        self._flow_engine = val

    def __repr__(self) -> str:
        ''' repr method '''
        return repr('Unit(Id:{}, Flow Engine:{}, Flow State:{}, Order Temp:{})'.format(self._unit_id,
                        self._flow_engine,
                        self._flow_state,
                        self._order_temp))

class NumUnitError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class FlowEngineError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class OrderTempError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class ClientNotConnectedError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg

class UpdateValueError(Exception):
    ''' user defined exception '''

    def __init__(self,
                    msg:str = "") -> None:
        ''' Class Constructor '''
        self._msg = msg

    def __str__(self):
        ''' print the message '''
        return self._msg