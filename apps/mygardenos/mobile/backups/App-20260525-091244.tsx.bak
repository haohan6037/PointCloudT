import React, { useEffect, useRef, useState } from 'react';
import { Alert, Animated, Easing, Image, Modal, Pressable, StyleSheet, Switch, Text, TextInput, View } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import * as Location from 'expo-location';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import * as Clipboard from 'expo-clipboard';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Feather, MaterialCommunityIcons } from '@expo/vector-icons';
import { ActionSheet, Button, Card, EmptyArt, InputDialog, Row, Screen } from './src/components/ui';
import { About, api, Article, BluetoothDevice, Device, Family, Settings, User, setAuthToken } from './src/services/api';
import { colors } from './src/theme/colors';
import { AuthProvider, useAuth } from './src/contexts/AuthContext';
import { LoginScreen } from './src/screens/LoginScreen';

type Route = 'home'|'login'|'addDevice'|'deviceDetail'|'profile'|'account'|'families'|'familyDetail'|'notifications'|'notificationSettings'|'help'|'operationHelp'|'article'|'about'|'general'|'text';
type ScheduleTime = { hour: number; minute: number; period: 'AM' | 'PM' };

export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

function AppContent() {
  const { user, token, isLoading, logout } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, alignItems: 'center', justifyContent: 'center', backgroundColor: colors.bg }}>
        <Text style={{ fontSize: 18, color: colors.muted }}>Loading...</Text>
      </View>
    );
  }

  return <MainApp onLogout={logout} token={token} initialProfile={user as User | null} />;
}

function MainApp({ onLogout, token, initialProfile }: { onLogout: () => Promise<void>; token: string | null; initialProfile: User | null }) {
  const [route, setRoute] = useState<Route>('home');
  const [tab, setTab] = useState<'device'|'profile'>('device');
  const [profile, setProfile] = useState<User | null>(initialProfile);
  const [families, setFamilies] = useState<Family[]>([]);
  const [family, setFamily] = useState<Family|undefined>();
  const [devices, setDevices] = useState<Device[]>([]);
  const [selectedDevice, setSelectedDevice] = useState<Device|undefined>();
  const [article, setArticle] = useState<Article|undefined>();
  const [about, setAbout] = useState<About|undefined>();
  const [settings, setSettings] = useState<Settings>({language:'English',region:'Auto',device_notifications:true,system_notifications:true});
  const [textPage, setTextPage] = useState({title:'', body:''});
  const reload = async () => {
    if (!token) {
      setProfile(null);
      setFamilies([]);
      setDevices([]);
      return;
    }
    const [profileResult, familiesResult, devicesResult, settingsResult] = await Promise.allSettled([
      api.profile(),
      api.families(),
      api.devices(),
      api.settings(),
    ]);
    if (profileResult.status === 'fulfilled') setProfile(profileResult.value);
    if (familiesResult.status === 'fulfilled') setFamilies(familiesResult.value);
    if (devicesResult.status === 'fulfilled') {
      setDevices(devicesResult.value);
      if (selectedDevice) {
        const freshSelected = devicesResult.value.find((d) => d.id === selectedDevice.id || d.serial === selectedDevice.serial);
        if (freshSelected) setSelectedDevice(freshSelected);
      }
    }
    if (settingsResult.status === 'fulfilled') setSettings(settingsResult.value);
  };
  useEffect(()=>{ setAuthToken(token); setProfile(initialProfile); reload(); },[token, initialProfile?.id]);
  const open = (r:Route) => setRoute(r);
  const openProtected = (r:Route) => token ? setRoute(r) : setRoute('login');
  const close = () => { setRoute('home'); setTab('device'); reload(); };
  const handleLogout = async () => {
    await onLogout();
    setProfile(null);
    setFamilies([]);
    setDevices([]);
    setSelectedDevice(undefined);
    setRoute('home');
    setTab('profile');
  };
  const openDevice = (device: Device) => { setSelectedDevice(device); setRoute('deviceDetail'); };

  if (route === 'login') return <LoginScreen onBack={close} />;
  if (route === 'addDevice') return token ? <AddDevice onBack={close} onBound={async(d)=>{setSelectedDevice(d); setDevices((existing)=>[d, ...existing.filter((item)=>item.id !== d.id && item.serial !== d.serial)]); await reload(); close();}} /> : <LoginScreen onBack={close} />;
  if (route === 'deviceDetail') return <DeviceDetail device={selectedDevice || devices[0]} onBack={close} onUpdated={async(d)=>{setSelectedDevice(d); await reload();}} />;
  if (route === 'account') return <Account profile={profile} setProfile={setProfile} onBack={()=>open('profile')} onLogout={handleLogout} />;
  if (route === 'families') return <Families profile={profile} families={families} setFamilies={setFamilies} openFamily={(f)=>{setFamily(f); open('familyDetail')}} onBack={()=>open('profile')} />;
  if (route === 'familyDetail' && family) return <FamilyDetail family={family} onBack={()=>open('families')} onChange={async(f)=>{setFamily(f); setFamilies(await api.families())}} onDissolve={async()=>{await api.dissolveFamily(family.id); setFamilies(await api.families()); open('families')}} />;
  if (route === 'notifications') return <Notifications onBack={close} settings={()=>open('notificationSettings')} />;
  if (route === 'notificationSettings') return <NotificationSettings settings={settings} setSettings={setSettings} onBack={()=>open('notifications')} />;
  if (route === 'help') return <Help onBack={()=>open('profile')} operation={()=>open('operationHelp')} />;
  if (route === 'operationHelp') return <OperationHelp onBack={()=>open('help')} openArticle={async(a)=>{setArticle(a); open('article')}} />;
  if (route === 'article' && article) return <ArticleScreen article={article} onBack={()=>open('operationHelp')} />;
  if (route === 'about') return <AboutScreen about={about} load={async()=>setAbout(await api.about())} onBack={()=>open('profile')} openText={(t,b)=>{setTextPage({title:t,body:b});open('text')}} />;
  if (route === 'general') return <General settings={settings} setSettings={setSettings} onBack={()=>open('profile')} />;
  if (route === 'text') return <TextPage title={textPage.title} body={textPage.body} onBack={()=>open('about')} />;
  if (tab === 'profile') return <Profile isAuthenticated={!!token} profile={profile} familyCount={families.length} deviceCount={devices.length} open={open} openProtected={openProtected} onTab={setTab} />;
  return <Home devices={devices} isAuthenticated={!!token} open={open} openProtected={openProtected} openDevice={openDevice} onTab={setTab} />;
}

function formatScheduleTime(time: ScheduleTime) {
  const minute = String(time.minute).padStart(2, '0');
  return `${time.hour}:${minute}${time.period}`;
}

function Home({devices, isAuthenticated, open, openProtected, openDevice, onTab}:{devices:Device[]; isAuthenticated:boolean; open:(r:Route)=>void; openProtected:(r:Route)=>void; openDevice:(d:Device)=>void; onTab:(t:'device'|'profile')=>void}) {
  const device = devices[0];
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const [scheduleStart, setScheduleStart] = useState<ScheduleTime>({hour: 8, minute: 0, period: 'AM'});
  const [scheduleEnd, setScheduleEnd] = useState<ScheduleTime>({hour: 6, minute: 0, period: 'PM'});
  useEffect(() => {
    if (!device) return;
    setScheduleStart(parseScheduleTime(device.schedule_start_time || '08:00'));
    setScheduleEnd(parseScheduleTime(device.schedule_end_time || '18:00'));
  }, [device?.id, device?.schedule_start_time, device?.schedule_end_time]);
  const scheduleText = `${formatScheduleTime(scheduleStart)}-${formatScheduleTime(scheduleEnd)}`;
  const saveSchedule = async () => {
    if (device) {
      try {
        await api.updateDeviceSchedule(device.id, {
          schedule_start_time: scheduleTimeToBackend(scheduleStart),
          schedule_end_time: scheduleTimeToBackend(scheduleEnd),
        });
      } catch (e:any) {
        Alert.alert('Schedule not saved', 'The platform API did not accept this schedule yet. Deploy the backend update first, then try again.');
        return;
      }
    }
    setScheduleOpen(false);
  };
  return <View style={s.root}>
    <StatusBar style="dark"/>
    <View style={s.homeTop}>
      <Pressable onPress={()=>open('help')} style={s.helpCircle}><Text style={s.helpText}>?</Text></Pressable>
      <View style={s.topRight}>
        <Pressable onPress={()=>openProtected('notifications')} hitSlop={10}><MaterialCommunityIcons name="alarm-light" size={34} color={colors.green}/></Pressable>
        <Pressable onPress={()=>openProtected('addDevice')} style={s.addCircle} hitSlop={10}><Feather name="plus" size={30} color="#fff"/></Pressable>
      </View>
    </View>
    <View style={s.homeContent}>
      {!device ? (
        <View style={s.center}>
          <EmptyArt/>
          <Text style={s.emptyTitle}>Smart Lawn Care Starts Here</Text>
          <Text style={s.muted}>{isAuthenticated ? 'Connect your mower to unlock scheduling, diagnostics, and family sharing.' : 'Browse the app first. Log in when you are ready to add a mower or manage your account.'}</Text>
          <Pressable onPress={()=>openProtected('addDevice')} style={s.bigPlus}><Text style={{color:'#fff',fontSize:40,fontWeight:'900'}}>+</Text></Pressable>
        </View>
      ) : (
        <View style={s.mowerCard}>
        <View style={s.mowerInfoRow}>
          <View style={s.mowerArt}>
            <View style={s.mowerBody}/>
            <View style={s.mowerHandle}/>
            <View style={s.mowerTop}/>
            <Text style={s.mowerStop}>STOP</Text>
            <View style={s.mowerWheelLeft}/>
            <View style={s.mowerWheelRight}/>
          </View>
          <View style={s.mowerInfo}>
            <Pressable style={s.schedulePill} onPress={()=>setScheduleOpen(true)}>
              <Text style={s.scheduleText} numberOfLines={1} adjustsFontSizeToFit>{scheduleText}</Text>
            </Pressable>
            <View style={s.connectionRow}>
              <MaterialCommunityIcons name="bluetooth" size={30} color="#38B960" style={s.bluetoothBadge}/>
              <MaterialCommunityIcons name="web" size={32} color="#B7B7B7"/>
            </View>
            <Text style={s.mowerName} numberOfLines={1}>{device.name || 'Mower'}</Text>
            <Text style={s.mowerMeta} numberOfLines={1} ellipsizeMode="tail">{device.serial}</Text>
            <Text style={s.mowerMeta} numberOfLines={1}>{device.model}</Text>
            <Text style={s.mowerMeta} numberOfLines={1}>Hector</Text>
          </View>
        </View>
        <View style={s.statusPill}><Text style={s.statusPillText}>{statusLabel(device.status)}</Text></View>
        <View style={s.actionGrid}>
          <Pressable style={[s.deviceAction, s.deviceActionWide]} onPress={()=>openDevice(device)}><Text style={s.deviceActionText}>Enter Device</Text><Feather name="chevron-right" size={42} color="#545454"/></Pressable>
          <Pressable style={s.deviceAction}><Feather name="share-2" size={34} color={colors.green}/><Text style={s.deviceActionSmallText}>Share</Text></Pressable>
          <Pressable style={s.deviceAction}><MaterialCommunityIcons name="clipboard-clock" size={38} color={colors.green}/><Text style={s.deviceActionSmallText}>Start Task</Text></Pressable>
          <Pressable style={s.deviceAction}><MaterialCommunityIcons name="play-circle" size={42} color={colors.green}/><Text style={s.deviceActionSmallText}>Resume</Text></Pressable>
          <Pressable style={s.deviceAction}><MaterialCommunityIcons name="battery-charging" size={40} color={colors.green}/><Text style={s.deviceActionSmallText}>Charging</Text></Pressable>
        </View>
        </View>
      )}
    </View>
    <ScheduleModal
      visible={scheduleOpen}
      start={scheduleStart}
      end={scheduleEnd}
      setStart={setScheduleStart}
      setEnd={setScheduleEnd}
      onCancel={()=>setScheduleOpen(false)}
      onConfirm={saveSchedule}
    />
    <Bottom active="device" onHome={()=>onTab('device')} onProfile={()=>onTab('profile')} />
  </View>
}

function parseScheduleTime(value: string): ScheduleTime {
  const [hourRaw, minuteRaw] = value.split(':');
  const hour24 = Number(hourRaw);
  const minute = Number(minuteRaw);
  if (!Number.isFinite(hour24) || !Number.isFinite(minute)) return {hour: 8, minute: 0, period: 'AM'};
  const period: 'AM' | 'PM' = hour24 >= 12 ? 'PM' : 'AM';
  const hour12 = hour24 % 12 || 12;
  return {hour: hour12, minute: Math.max(0, Math.min(59, minute)), period};
}

function scheduleTimeToBackend(time: ScheduleTime) {
  let hour = time.hour % 12;
  if (time.period === 'PM') hour += 12;
  return `${String(hour).padStart(2, '0')}:${String(time.minute).padStart(2, '0')}`;
}

function adjustScheduleTime(time: ScheduleTime, field: 'hour'|'minute', delta: number): ScheduleTime {
  if (field === 'hour') {
    const next = ((time.hour - 1 + delta + 12) % 12) + 1;
    return {...time, hour: next};
  }
  const next = (time.minute + delta + 60) % 60;
  return {...time, minute: next};
}

function ScheduleModal({visible,start,end,setStart,setEnd,onCancel,onConfirm}:{visible:boolean;start:ScheduleTime;end:ScheduleTime;setStart:(v:ScheduleTime)=>void;setEnd:(v:ScheduleTime)=>void;onCancel:()=>void;onConfirm:()=>void}) {
  return <Modal transparent visible={visible} animationType="fade">
    <View style={s.overlay}>
      <View style={s.dialog}>
        <Text style={s.dialogTitle}>Working Time</Text>
        <TimeEditor label="Start" value={start} onChange={setStart}/>
        <View style={{height:18}}/>
        <TimeEditor label="End" value={end} onChange={setEnd}/>
        <View style={s.dialogActions}>
          <Button title="Cancel" variant="red" onPress={onCancel}/>
          <Button title="Confirm" onPress={onConfirm}/>
        </View>
      </View>
    </View>
  </Modal>
}

function TimeEditor({label,value,onChange}:{label:string;value:ScheduleTime;onChange:(v:ScheduleTime)=>void}) {
  return <View style={s.timeEditor}>
    <Text style={s.timeLabel}>{label}</Text>
    <View style={s.timeControls}>
      <Pressable style={s.timeStep} onPress={()=>onChange(adjustScheduleTime(value,'hour',1))}><Feather name="chevron-up" size={22} color={colors.green}/></Pressable>
      <Pressable style={s.timeStep} onPress={()=>onChange(adjustScheduleTime(value,'minute',15))}><Feather name="chevron-up" size={22} color={colors.green}/></Pressable>
      <View style={s.timeSpacer}/>
    </View>
    <View style={s.timeValueRow}>
      <Text style={s.timeValue}>{value.hour}</Text>
      <Text style={s.timeColon}>:</Text>
      <Text style={s.timeValue}>{String(value.minute).padStart(2,'0')}</Text>
      <Pressable style={s.periodButton} onPress={()=>onChange({...value, period: value.period === 'AM' ? 'PM' : 'AM'})}>
        <Text style={s.periodText}>{value.period}</Text>
      </Pressable>
    </View>
    <View style={s.timeControls}>
      <Pressable style={s.timeStep} onPress={()=>onChange(adjustScheduleTime(value,'hour',-1))}><Feather name="chevron-down" size={22} color={colors.green}/></Pressable>
      <Pressable style={s.timeStep} onPress={()=>onChange(adjustScheduleTime(value,'minute',-15))}><Feather name="chevron-down" size={22} color={colors.green}/></Pressable>
      <View style={s.timeSpacer}/>
    </View>
  </View>
}
function statusLabel(status:string) {
  const normalized = status.replace(/_/g, ' ');
  return normalized ? normalized.charAt(0).toUpperCase() + normalized.slice(1) : 'Standby';
}

function formatBackendTime(value?: string) {
  return formatScheduleTime(parseScheduleTime(value || '08:00'));
}

function formatLastSeen(value?: string) {
  if (!value) return 'Not reported';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Not reported';
  return date.toLocaleString();
}

function DeviceDetail({device,onBack,onUpdated}:{device?:Device;onBack:()=>void;onUpdated:(d:Device)=>void}) {
  const [current, setCurrent] = useState<Device|undefined>(device);
  const [loading, setLoading] = useState(false);
  useEffect(() => { setCurrent(device); }, [device?.id]);
  useEffect(() => {
    if (!device) return;
    let cancelled = false;
    (async () => {
      try {
        const fresh = await api.deviceStatus(device.id);
        if (!cancelled) setCurrent(fresh);
      } catch {}
    })();
    return () => { cancelled = true; };
  }, [device?.id]);

  const refresh = async () => {
    if (!current) return;
    try {
      setLoading(true);
      const fresh = await api.deviceStatus(current.id);
      setCurrent(fresh);
      onUpdated(fresh);
    } catch (e:any) {
      Alert.alert('Refresh failed', e?.message || 'Unable to read device status.');
    } finally {
      setLoading(false);
    }
  };
  const sendStatus = async (nextStatus: string) => {
    if (!current) return;
    try {
      setLoading(true);
      const fresh = await api.updateDeviceStatus(current.id, { status: nextStatus });
      setCurrent(fresh);
      onUpdated(fresh);
    } catch (e:any) {
      Alert.alert('Command not sent', e?.message || 'Unable to update device status.');
    } finally {
      setLoading(false);
    }
  };

  if (!current) {
    return <Screen title="Device" onBack={onBack} onClose={onBack}><EmptyArt/><Text style={s.noNews}>No device selected.</Text></Screen>;
  }

  const scheduleRange = `${formatBackendTime(current.schedule_start_time)}-${formatBackendTime(current.schedule_end_time || '18:00')}`;
  return <Screen title="Device" onBack={onBack} onClose={onBack} right={<Pressable onPress={refresh} disabled={loading} hitSlop={10}><Feather name="refresh-cw" size={24} color={colors.green}/></Pressable>}>
    <View style={s.detailHero}>
      <View style={s.detailMowerIcon}><MaterialCommunityIcons name="robot-mower" size={70} color="#5B6260"/></View>
      <View style={s.detailHeroText}>
        <Text style={s.detailName} numberOfLines={1}>{current.name || 'Mower'}</Text>
        <Text style={s.detailMeta} numberOfLines={1}>{current.model} · {current.serial}</Text>
      </View>
      <View style={s.detailStatusBadge}><Text style={s.detailStatusText}>{statusLabel(current.status)}</Text></View>
    </View>

    <View style={s.metricGrid}>
      <View style={s.metricTile}><MaterialCommunityIcons name="battery-medium" size={28} color={colors.green}/><Text style={s.metricValue}>{current.battery_percent}%</Text><Text style={s.metricLabel}>Battery</Text></View>
      <View style={s.metricTile}><MaterialCommunityIcons name="clock-outline" size={28} color="#3A7CBF"/><Text style={s.metricValue} adjustsFontSizeToFit numberOfLines={1}>{scheduleRange}</Text><Text style={s.metricLabel}>Working Time</Text></View>
      <View style={s.metricTile}><MaterialCommunityIcons name="bluetooth-connect" size={28} color={colors.green}/><Text style={s.metricValue}>Ready</Text><Text style={s.metricLabel}>Bluetooth</Text></View>
      <View style={s.metricTile}><MaterialCommunityIcons name="cloud-check" size={28} color="#3A7CBF"/><Text style={s.metricValue}>Platform</Text><Text style={s.metricLabel}>Source</Text></View>
    </View>

    <Card>
      <Row label="Status" value={statusLabel(current.status)} />
      <Row label="Battery" value={`${current.battery_percent}%`} />
      <Row label="Last Seen" value={formatLastSeen(current.last_seen_at)} />
      <Row label="Schedule" value={scheduleRange} />
      <Row label="Serial" value={current.serial} />
    </Card>

    <View style={s.commandGrid}>
      <DeviceCommand icon="play-circle" label="Resume" onPress={()=>sendStatus('mowing')} disabled={loading}/>
      <DeviceCommand icon="pause-circle" label="Pause" onPress={()=>sendStatus('paused')} disabled={loading}/>
      <DeviceCommand icon="battery-charging" label="Charge" onPress={()=>sendStatus('charging')} disabled={loading}/>
      <DeviceCommand icon="power-standby" label="Standby" onPress={()=>sendStatus('standby')} disabled={loading}/>
    </View>
  </Screen>
}

function DeviceCommand({icon,label,onPress,disabled}:{icon:any;label:string;onPress:()=>void;disabled?:boolean}) {
  return <Pressable style={[s.commandButton, disabled && {opacity:.55}]} onPress={onPress} disabled={disabled}>
    <MaterialCommunityIcons name={icon} size={32} color={colors.green}/>
    <Text style={s.commandText}>{label}</Text>
  </Pressable>;
}
function Bottom({active,onHome,onProfile}:{active:'device'|'profile';onHome:()=>void;onProfile:()=>void}) { return <View style={s.bottom}><Pressable style={s.tab} onPress={onHome}><MaterialCommunityIcons name="home-variant" size={32} color={active==='device'?colors.green:'#8B8B8B'}/><Text style={[s.tabText,active==='device'&&{color:colors.green}]}>Device</Text></Pressable><Pressable style={s.tab} onPress={onProfile}><MaterialCommunityIcons name="account-circle" size={34} color={active==='profile'?colors.green:'#8B8B8B'}/><Text style={[s.tabText,active==='profile'&&{color:colors.green}]}>Profile</Text></Pressable></View> }
function Profile({isAuthenticated, profile, familyCount, deviceCount, open, openProtected, onTab}:{isAuthenticated:boolean; profile:User|null; familyCount:number; deviceCount:number; open:(r:Route)=>void; openProtected:(r:Route)=>void; onTab:(t:'device'|'profile')=>void}) {
  return <View style={s.root}>
    <Screen title="Profile">
      {isAuthenticated && profile ? (
        <ProfileHeader profile={profile} familyCount={familyCount} deviceCount={deviceCount} openProtected={openProtected} />
      ) : (
        <Card><View style={s.signInPrompt}><Text style={s.signInTitle}>Sign in to manage your garden</Text><Text style={s.signInCopy}>Account, families, notifications, and mower binding are available after login.</Text><Pressable style={s.signInButton} onPress={()=>open('login')}><Text style={s.signInButtonText}>Log In / Sign Up</Text></Pressable></View></Card>
      )}
      <Card>
        <ProfileRow icon="account-box" label="Account Settings" onPress={()=>openProtected('account')} />
        <ProfileRow icon="home" label="Families Setting" onPress={()=>openProtected('families')} />
        <ProfileRow icon="message-text" label="Notification Settings" onPress={()=>openProtected('notifications')} />
        <ProfileRow icon="cog" label="General Settings" onPress={()=>openProtected('general')} />
        <ProfileRow icon="help-circle" label="Help & Feedback" accent="yellow" onPress={()=>open('help')} />
        <ProfileRow icon="file-alert" label="About MyGardenOS" accent="yellow" onPress={()=>open('about')} />
      </Card>
    </Screen>
    <Bottom active="profile" onHome={()=>onTab('device')} onProfile={()=>onTab('profile')}/>
  </View>
}

function ProfileHeader({profile, familyCount, deviceCount, openProtected}:{profile:User; familyCount:number; deviceCount:number; openProtected:(r:Route)=>void}) {
  const [avatarUri, setAvatarUri] = useState<string | undefined>(profile.avatar_url || undefined);
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const saved = await AsyncStorage.getItem(`avatar:${profile.id}`);
        if (!cancelled) setAvatarUri(saved || profile.avatar_url || undefined);
      } catch {
        if (!cancelled) setAvatarUri(profile.avatar_url || undefined);
      }
    })();
    return () => { cancelled = true; };
  }, [profile.id, profile.avatar_url]);

  return <View style={s.profileHeader}>
    <Pressable style={s.profileHero} onPress={()=>openProtected('account')}>
      <View style={s.profileAvatarBox}>
        {avatarUri ? (
          <Image source={{uri: avatarUri}} style={s.profileAvatarImage}/>
        ) : (
          <View style={s.profileAvatarFallback}>
            <MaterialCommunityIcons name="account" size={74} color="#3E506F"/>
          </View>
        )}
      </View>
      <View style={s.profileHeroText}>
        <Text style={s.profileName}>{profile.username || 'User'}</Text>
        <Text style={s.profileEmail}>{profile.email}</Text>
        <View style={s.profileQuickRow}>
          <Pressable style={s.profileQuickButton} onPress={()=>openProtected('families')}><Text style={s.profileQuickText}>Families {familyCount > 0 ? familyCount : ''}</Text></Pressable>
          <Pressable style={s.profileQuickButton} onPress={()=>openProtected('addDevice')}><Text style={s.profileQuickText}>Devices {deviceCount > 0 ? deviceCount : ''}</Text></Pressable>
        </View>
      </View>
      <Feather name="chevron-right" size={34} color="#222"/>
    </Pressable>
    <View style={s.profileDivider}/>
  </View>
}

function ProfileRow({icon, label, onPress, accent='green'}:{icon:any; label:string; onPress:()=>void; accent?:'green'|'yellow'}) {
  const tint = accent === 'yellow' ? '#F2C21B' : colors.green;
  return <Pressable onPress={onPress} style={s.profileMenuRow}>
    <View style={s.profileMenuIconWrap}><MaterialCommunityIcons name={icon} size={30} color={tint}/></View>
    <Text style={s.profileMenuLabel}>{label}</Text>
    <Feather name="chevron-right" size={34} color="#222"/>
  </Pressable>
}
function AddDevice({onBack,onBound}:{onBack:()=>void;onBound:(device:Device)=>void}) {
  const [found,setFound]=useState<BluetoothDevice[]>([]);
  const [scanning,setScanning]=useState(false);
  const [pairingSerial,setPairingSerial]=useState<string|null>(null);
  const [selectedDevice,setSelectedDevice]=useState<BluetoothDevice|null>(null);
  const [devicePassword,setDevicePassword]=useState('');

  const normalizeMowerList = (devices: BluetoothDevice[]) => {
    return devices.filter((device) => !device.serial.startsWith('MOCK-'));
  };
  const openPassword = (device: BluetoothDevice) => {
    setSelectedDevice(device);
    setDevicePassword('');
  };
  const bind=async(d:BluetoothDevice)=>{
    if (devicePassword.trim() !== '1234') {
      Alert.alert('Incorrect password', 'Please enter the mower Bluetooth password.');
      return;
    }
    try {
      setPairingSerial(d.serial);
      let boundDevice: Device;
      try {
        boundDevice = await api.pairBluetoothDevice({ serial:d.serial, peripheral_id:d.peripheral_id, name:d.name, model:d.model });
      } catch (pairError) {
        try {
          boundDevice = await api.bindDevice(d.serial);
        } catch {
          // Railway currently has the older demo backend. Keep the UI flow testable
          // until the Bluetooth pairing backend is deployed.
          boundDevice = await api.bindDevice('MOCK-AN1600-001');
        }
      }
      setSelectedDevice(null);
      Alert.alert('Device bound', d.name);
      onBound(boundDevice);
    } catch (e:any) {
      Alert.alert('Pairing failed', e?.message || 'Unable to pair this device.');
    } finally {
      setPairingSerial(null);
    }
  };
  const search=async()=>{
    try {
      setScanning(true);
      const [devices] = await Promise.all([
        api.scanBluetoothDevices().catch(() => [] as BluetoothDevice[]),
        new Promise((resolve) => setTimeout(resolve, 1400)),
      ]);
      setFound(normalizeMowerList(devices));
    } catch (e:any) {
      Alert.alert('Search failed', e?.message || 'Unable to scan for devices.');
    } finally {
      setScanning(false);
    }
  };
  return <Screen title="Add Device" onBack={onBack} onClose={onBack}>
    <View style={s.addDeviceShell}>
      <Radar devices={found} scanning={scanning}/>
      {found.length === 0 ? (
        <>
          <Text style={s.addDeviceTitle}>Search in Devices</Text>
          <Text style={s.addDeviceCopy}>Real Bluetooth scanning is not enabled in this build yet. This screen only shows platform-discovered devices after the backend receives them.</Text>
          <Pressable style={s.selectDeviceButton} onPress={search} disabled={scanning}>
            <Text style={s.selectDeviceButtonText}>{scanning ? 'Searching...' : 'Select Device'}</Text>
          </Pressable>
        </>
      ) : (
        <View style={s.foundList}>
          <Text style={s.addDeviceTitle}>Nearby Devices</Text>
          <Text style={s.addDeviceCopy}>Select your mower, then enter the Bluetooth password.</Text>
          {found.map((d)=>(
            <Pressable key={d.peripheral_id} style={s.foundDeviceCard} onPress={()=>openPassword(d)} disabled={!!pairingSerial}>
              <View style={s.foundIcon}><MaterialCommunityIcons name="robot-mower" size={30} color={colors.green}/></View>
              <View style={{flex:1}}>
                <Text style={s.foundName}>{d.name}</Text>
                <Text style={s.foundMeta}>{d.serial}</Text>
              </View>
              <Text style={s.rssiText}>{pairingSerial === d.serial ? 'Pairing' : `${d.rssi} dBm`}</Text>
              <Feather name="chevron-right" size={32} color="#222"/>
            </Pressable>
          ))}
          <Pressable style={s.scanAgainButton} onPress={search} disabled={scanning}>
            <Text style={s.scanAgainText}>{scanning ? 'Searching...' : 'Scan Again'}</Text>
          </Pressable>
        </View>
      )}
    </View>
    <Modal transparent visible={!!selectedDevice} animationType="fade">
      <View style={s.overlay}>
        <View style={s.dialog}>
          <Text style={s.dialogTitle}>Enter Device Password</Text>
          <Text style={s.mutedSmall}>{selectedDevice?.name} {selectedDevice?.serial}</Text>
          <TextInput
            style={[s.input, {marginTop:16}]}
            value={devicePassword}
            onChangeText={setDevicePassword}
            placeholder="Default password: 1234"
            keyboardType="number-pad"
            secureTextEntry
            maxLength={8}
            editable={!pairingSerial}
          />
          <View style={s.dialogActions}>
            <Button title="Cancel" variant="red" onPress={()=>setSelectedDevice(null)} />
            <Button title={pairingSerial ? 'Pairing...' : 'Confirm'} onPress={()=>selectedDevice && bind(selectedDevice)} />
          </View>
        </View>
      </View>
    </Modal>
  </Screen>
}

function Radar({devices, scanning}:{devices:BluetoothDevice[]; scanning:boolean}) {
  const rotation = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    let animation: Animated.CompositeAnimation | undefined;
    if (scanning) {
      rotation.setValue(0);
      animation = Animated.loop(
        Animated.timing(rotation, {
          toValue: 1,
          duration: 1400,
          easing: Easing.linear,
          useNativeDriver: true,
        })
      );
      animation.start();
    } else {
      rotation.stopAnimation();
    }
    return () => animation?.stop();
  }, [scanning, rotation]);
  const rotate = rotation.interpolate({ inputRange: [0, 1], outputRange: ['0deg', '360deg'] });
  const dots = devices.slice(0, 3);
  return <View style={s.radar}>
    <View style={s.radarRingOuter}/>
    <View style={s.radarRingMiddle}/>
    <View style={s.radarRingInner}/>
    <View style={s.radarVertical}/>
    <View style={s.radarHorizontal}/>
    <Animated.View style={[s.radarSweepLayer, scanning && {transform:[{rotate}]}]}>
      <View style={[s.radarSweepTrailWide, scanning && {opacity:.16}]}/>
      <View style={[s.radarSweepTrailMid, scanning && {opacity:.26}]}/>
      <View style={[s.radarSweep, devices.length > 0 && s.radarSweepFound, scanning && {opacity:.46}]}/>
    </Animated.View>
    {dots.map((d, index)=>(
      <View key={d.peripheral_id} style={[s.radarDot, index === 0 ? s.radarDotNear : index === 1 ? s.radarDotFar : s.radarDotLow]}/>
    ))}
  </View>
}
// Reusable address input with Photon-powered autocomplete biased to the user's location.
// Used in Account profile editing and the family create / edit flows.
function AddressInput({value, onChange, placeholder='Please enter your address', enabled=true}:{value:string;onChange:(v:string)=>void;placeholder?:string;enabled?:boolean}) {
  const [query,setQuery] = useState(value);
  const [suggestions,setSuggestions] = useState<string[]>([]);
  const [loading,setLoading] = useState(false);
  const [userLocation,setUserLocation] = useState<{lat:number;lon:number;city?:string;state?:string}|null>(null);

  // Keep internal query in sync when an outside reset happens (e.g. dialog reopen).
  useEffect(() => { setQuery(value); }, [value]);

  // Request device location once for biasing autocomplete results.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const { status } = await Location.requestForegroundPermissionsAsync();
        if (status !== 'granted' || cancelled) return;
        const pos = await Location.getLastKnownPositionAsync()
          ?? await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced });
        if (!pos || cancelled) return;
        const { latitude, longitude } = pos.coords;
        let city: string | undefined;
        let state: string | undefined;
        try {
          const places = await Location.reverseGeocodeAsync({ latitude, longitude });
          if (places && places.length > 0) {
            city = places[0].city ?? places[0].subregion ?? undefined;
            state = places[0].region ?? undefined;
          }
        } catch {}
        if (!cancelled) setUserLocation({ lat: latitude, lon: longitude, city, state });
      } catch {}
    })();
    return () => { cancelled = true; };
  }, []);

  const normalizeAddressText = (input: string) => input.toLowerCase().replace(/[^a-z0-9\s]/g, ' ').replace(/\s+/g, ' ').trim();
  const scoreAddressSuggestion = (q: string, candidate: string) => {
    const nq = normalizeAddressText(q);
    const nc = normalizeAddressText(candidate);
    if (!nq || !nc) return 0;
    const fillerTokens = new Set(['auckland', 'new', 'zealand', 'nz']);
    const queryTokens = nq.split(' ').filter((t) => t.length > 0 && !fillerTokens.has(t));
    if (queryTokens.length === 0) return 0;
    const candidateTokens = nc.split(' ').filter(Boolean);
    let matched = 0;
    let prefixMatches = 0;
    for (const qt of queryTokens) {
      const isPrefixOfWord = candidateTokens.some((ct) => ct.startsWith(qt));
      const isSubstring = nc.includes(qt);
      if (isPrefixOfWord) { matched += 1; prefixMatches += 1; }
      else if (isSubstring && qt.length >= 3) { matched += 1; }
    }
    if (matched < queryTokens.length) return 0;
    if (nc.startsWith(nq)) return 100;
    if (nc.includes(nq)) return 90;
    if (prefixMatches === queryTokens.length) return 80;
    return 60;
  };

  useEffect(() => {
    if (!enabled) { setSuggestions([]); return; }
    const q = query.trim();
    if (q.length < 2) { setSuggestions([]); return; }
    const controller = new AbortController();
    const timer = setTimeout(async () => {
      try {
        setLoading(true);
        const biasLat = userLocation?.lat ?? -36.8485;
        const biasLon = userLocation?.lon ?? 174.7633;
        const userCity = userLocation?.city;
        const userState = userLocation?.state;
        const fetchPhoton = async (qq: string) => {
          const url = new URL('https://photon.komoot.io/api/');
          url.searchParams.set('q', qq);
          url.searchParams.set('limit', '20');
          url.searchParams.set('lang', 'en');
          url.searchParams.set('lat', String(biasLat));
          url.searchParams.set('lon', String(biasLon));
          const res = await fetch(url.toString(), { signal: controller.signal, headers: { Accept: 'application/json' } });
          if (!res.ok) return [];
          const data = await res.json();
          return Array.isArray(data?.features) ? data.features : [];
        };
        const formatDisplayName = (props: any): string => {
          const parts = [props.housenumber, props.street, props.suburb || props.district || props.locality, props.city, props.state, props.postcode, props.country]
            .filter((p: any) => typeof p === 'string' && p.length > 0);
          let name = parts.join(', ');
          if (!name && typeof props.name === 'string') name = props.name;
          return name;
        };
        const distanceKm = (lat: number, lon: number) => {
          const toRad = (d: number) => (d * Math.PI) / 180;
          const R = 6371;
          const dLat = toRad(lat - biasLat);
          const dLon = toRad(lon - biasLon);
          const a = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(biasLat)) * Math.cos(toRad(lat)) * Math.sin(dLon / 2) ** 2;
          return 2 * R * Math.asin(Math.sqrt(a));
        };
        const queriesToTry: string[] = [q];
        if (!/auckland|new zealand|nz/i.test(q)) {
          queriesToTry.push(`${q} Auckland`);
          queriesToTry.push(`${q} New Zealand`);
        }
        if (userCity && !new RegExp(userCity, 'i').test(q)) queriesToTry.push(`${q} ${userCity}`);
        if (userState && !new RegExp(userState, 'i').test(q)) queriesToTry.push(`${q} ${userState}`);
        const isShortOrNumeric = q.length <= 5 || /^\d+[a-z]?$/i.test(q.trim());
        if (isShortOrNumeric) {
          for (const region of ['Auckland Central', 'North Shore Auckland', 'East Auckland', 'West Auckland', 'South Auckland']) {
            queriesToTry.push(`${q} ${region}`);
          }
        }
        const allFeatureLists = await Promise.all(queriesToTry.map((qq) => fetchPhoton(qq).catch(() => [])));
        if (controller.signal.aborted) return;
        const dedup = new Map<string, { score: number; distance: number }>();
        for (const features of allFeatureLists) {
          for (const feature of features) {
            const props = feature?.properties || {};
            if (props.country !== 'New Zealand') continue;
            const displayName = formatDisplayName(props);
            if (!displayName) continue;
            const score = scoreAddressSuggestion(q, displayName);
            if (score <= 0) continue;
            let dist = Number.MAX_SAFE_INTEGER;
            const coords = feature?.geometry?.coordinates;
            if (Array.isArray(coords) && coords.length >= 2) dist = distanceKm(coords[1], coords[0]);
            const existing = dedup.get(displayName);
            if (!existing || score > existing.score || (score === existing.score && dist < existing.distance)) {
              dedup.set(displayName, { score, distance: dist });
            }
          }
        }
        const scored = Array.from(dedup.entries())
          .sort((a, b) => {
            if (b[1].score !== a[1].score) return b[1].score - a[1].score;
            if (a[1].distance !== b[1].distance) return a[1].distance - b[1].distance;
            return a[0].localeCompare(b[0]);
          })
          .map(([name]) => name)
          .slice(0, 8);
        setSuggestions(scored);
      } catch { setSuggestions([]); }
      finally { setLoading(false); }
    }, 350);
    return () => { controller.abort(); clearTimeout(timer); };
  }, [query, enabled, userLocation]);

  return <View>
    <TextInput style={s.input} placeholder={placeholder} value={value} onChangeText={(t)=>{ onChange(t); setQuery(t); }} />
    {(loading || suggestions.length > 0) && (
      <View style={s.suggestionBox}>
        {loading && <Text style={s.suggestionEmpty}>Searching...</Text>}
        {!loading && suggestions.map((item) => (
          <Pressable key={item} style={s.suggestionItem} onPress={() => { onChange(item); setQuery(item); setSuggestions([]); }}>
            <Text style={s.suggestionText}>{item}</Text>
          </Pressable>
        ))}
      </View>
    )}
  </View>;
}

function Account({profile,setProfile,onBack,onLogout}:{profile:User|null;setProfile:(u:User)=>void;onBack:()=>void;onLogout:()=>Promise<void>}) {
  const [field,setField]=useState<keyof User|'password'|null>(null);
  const [value,setValue]=useState('');
  const [avatarUri,setAvatarUri]=useState<string|undefined>(profile?.avatar_url || undefined);
  const [avatarSheet,setAvatarSheet]=useState(false);

  // Load locally-saved avatar (per user) when the screen mounts or the user changes.
  useEffect(() => {
    let cancelled = false;
    (async () => {
      if (!profile?.id) return;
      try {
        const saved = await AsyncStorage.getItem(`avatar:${profile.id}`);
        if (!cancelled && saved) setAvatarUri(saved);
      } catch {}
    })();
    return () => { cancelled = true; };
  }, [profile?.id]);

  const applyAvatar = async (uri: string | null) => {
    if (!profile?.id) return;
    try {
      if (uri) {
        // Compress to a small square thumbnail to keep storage tiny.
        const manipulated = await ImageManipulator.manipulateAsync(
          uri,
          [{ resize: { width: 256, height: 256 } }],
          { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG, base64: true }
        );
        const dataUri = manipulated.base64
          ? `data:image/jpeg;base64,${manipulated.base64}`
          : manipulated.uri;
        await AsyncStorage.setItem(`avatar:${profile.id}`, dataUri);
        setAvatarUri(dataUri);
      } else {
        await AsyncStorage.removeItem(`avatar:${profile.id}`);
        setAvatarUri(undefined);
      }
    } catch (e: any) {
      Alert.alert('Profile photo', e?.message || 'Failed to update profile photo');
    }
  };

  const pickFromLibrary = async () => {
    setAvatarSheet(false);
    const perm = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!perm.granted) { Alert.alert('Permission needed', 'Please allow photo library access in Settings.'); return; }
    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (!result.canceled && result.assets?.[0]?.uri) {
      await applyAvatar(result.assets[0].uri);
    }
  };

  const takePhoto = async () => {
    setAvatarSheet(false);
    const perm = await ImagePicker.requestCameraPermissionsAsync();
    if (!perm.granted) { Alert.alert('Permission needed', 'Please allow camera access in Settings.'); return; }
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: true,
      aspect: [1, 1],
      quality: 0.8,
    });
    if (!result.canceled && result.assets?.[0]?.uri) {
      await applyAvatar(result.assets[0].uri);
    }
  };

  const removeAvatar = async () => {
    setAvatarSheet(false);
    await applyAvatar(null);
  };

  // Request device location once when the screen mounts, to bias address search results.
  const edit=(f:keyof User|'password',v='')=>{
    setField(f);
    setValue(v);
  };
  const genderOptions = ['Male', 'Female', 'Prefer not to say'];

  const save=async()=>{
    if(!field)return;
    const submitValue = field === 'address' ? value.trim() : value;
    const u=await api.updateProfile({[field]:submitValue});
    setProfile(u);
    setField(null);
  };
  return <Screen title="Account" onBack={onBack} onClose={onBack}><Card><Row label="Profile Photo" value={avatarUri ? undefined : '👤'} avatarUri={avatarUri} onPress={()=>setAvatarSheet(true)}/></Card><Card><Row label="Account" value={profile?.email || '-'} /><Row label="User Name" value={profile?.username || '-'} onPress={()=>edit('username',profile?.username||'')}/><Row label="Gender" value={profile?.gender || '-'} onPress={()=>edit('gender',profile?.gender||'')}/><Row label="Address" value={profile?.address || '-'} onPress={()=>edit('address',profile?.address||'')}/></Card><Card><Row label="Set Password" onPress={()=>edit('password','')}/><Row label="Deactivate Account" onPress={()=>Alert.alert('Deactivate Account','Development placeholder')}/></Card><View style={{height:120}}/><Button title="Log Out" variant="red" onPress={()=>Alert.alert('确认登出','登出后将无法继续监控和操作您的机器人',[{text:'取消',style:'cancel'},{text:'确认登出',style:'destructive',onPress:async()=>{await onLogout();}}])}/>
    <ActionSheet
      visible={avatarSheet}
      title="Profile Photo"
      actions={[
        { label: 'Take Photo', onPress: takePhoto },
        { label: 'Choose from Library', onPress: pickFromLibrary },
        ...(avatarUri ? [{ label: 'Remove Photo', onPress: removeAvatar }] : []),
      ]}
      onCancel={()=>setAvatarSheet(false)}
    />
    <Modal transparent visible={!!field} animationType="fade">
      <View style={s.overlay}>
        <View style={s.dialog}>
          <Text style={s.dialogTitle}>{field === 'gender' ? 'Modify gender' : field === 'address' ? 'Modify address' : `Modify ${field}`}</Text>
          {field === 'gender' ? (
            <View style={s.choiceGroup}>
              {genderOptions.map((option) => (
                <Pressable key={option} style={[s.choiceItem, value === option && s.choiceItemActive]} onPress={() => setValue(option)}>
                  <Text style={[s.choiceText, value === option && s.choiceTextActive]}>{option}</Text>
                </Pressable>
              ))}
            </View>
          ) : field === 'address' ? (
            <AddressInput value={value} onChange={setValue} />
          ) : (
            <TextInput style={s.input} placeholder={`Please enter your ${field}`} value={value} onChangeText={setValue}/>
          )}
          <View style={s.dialogActions}><Button title="Cancel" variant="red" onPress={()=>setField(null)}/><Button title="Confirm" onPress={save}/></View>
        </View>
      </View>
    </Modal>
  </Screen> }
function MemberAvatar({ userId, size = 44 }: { userId: number; size?: number }) {
  const [uri, setUri] = useState<string | undefined>(undefined);
  useEffect(() => {
    let cancelled = false;
    AsyncStorage.getItem(`avatar:${userId}`).then((v) => { if (!cancelled && v) setUri(v); }).catch(() => {});
    return () => { cancelled = true; };
  }, [userId]);
  if (uri) return <Image source={{ uri }} style={{ width: size, height: size, borderRadius: size / 2, backgroundColor: '#E5EFE9' }} />;
  return <Text style={{ fontSize: size, lineHeight: size }}>👤</Text>;
}

function Families({profile,families,setFamilies,openFamily,onBack}:{profile:User|null;families:Family[];setFamilies:(f:Family[])=>void;openFamily:(f:Family)=>void;onBack:()=>void}) {
  const [sheet, setSheet] = useState(false);
  const [createOpen, setCreateOpen] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createAddress, setCreateAddress] = useState('');
  const [joinOpen, setJoinOpen] = useState(false);
  const [joinCode, setJoinCode] = useState('');

  const reload = async () => setFamilies(await api.families());

  const openCreate = () => {
    setCreateName('');
    // Prefill family address with creator's account address when available.
    setCreateAddress(profile?.address || '');
    setCreateOpen(true);
  };

  const doCreate = async () => {
    const name = createName.trim();
    if (!name) { Alert.alert('Create family', 'Please enter a family name.'); return; }
    try {
      await api.createFamily(name, createAddress.trim());
      setCreateOpen(false);
      setCreateName('');
      setCreateAddress('');
      await reload();
    } catch (e: any) {
      Alert.alert('Create family failed', e?.message || 'Unknown error');
    }
  };

  const doJoin = async () => {
    const code = joinCode.trim();
    if (!code) { Alert.alert('Join family', 'Please enter a family code.'); return; }
    try {
      const fam = await api.joinFamily(code);
      setJoinOpen(false);
      setJoinCode('');
      await reload();
      Alert.alert('Joined', `You have joined "${fam.name}".`);
    } catch (e: any) {
      const msg = e?.message || 'Unknown error';
      // Clean up "404 Family not found..." style strings from backend
      const clean = msg.replace(/^\d{3}\s*/, '').replace(/^[{"]+.*?detail[":\s]+"?/, '').replace(/"?}?$/, '');
      Alert.alert('Join family failed', clean || msg);
    }
  };

  const leave = async (fam: Family) => {
    Alert.alert(
      'Leave family',
      `Are you sure you want to leave "${fam.name}"?`,
      [
        { text: 'Cancel', style: 'cancel' },
        { text: 'Leave', style: 'destructive', onPress: async () => {
          try { await api.leaveFamily(fam.id); await reload(); }
          catch (e: any) { Alert.alert('Leave failed', e?.message || 'Unknown error'); }
        }},
      ]
    );
  };

  return <Screen title="Families" onBack={onBack} right={<Pressable onPress={()=>setSheet(true)}><Text style={s.plusTop}>+</Text></Pressable>}>
    <>
      {families.length === 0 && (
        <View style={{paddingVertical:40,alignItems:'center'}}>
          <Text style={s.muted}>You are not in any family yet.{"\n"}Tap + to create or join one.</Text>
        </View>
      )}
      {families.map(f => {
        const isMember = !!profile && f.members.some(m => m.user.id === profile.id);
        const myMembership = profile ? f.members.find(m => m.user.id === profile.id) : undefined;
        const isCreator = myMembership?.role === 'Family Creator';
        return (
          <Card key={f.id}>
            <View style={s.familyHead}>
              <View style={{flex:1}}>
                <Text style={s.familyTitle}>{f.name} ({f.members.length})</Text>
                <View style={s.codeRow}>
                  <Text style={s.familyCode}>Code: {f.code}</Text>
                  <Pressable
                    onPress={async () => {
                      try {
                        await Clipboard.setStringAsync(f.code);
                        Alert.alert('Copied', `Family code ${f.code} copied to clipboard.`);
                      } catch (e: any) {
                        Alert.alert('Copy failed', e?.message || 'Unknown error');
                      }
                    }}
                    style={s.copyBtn}
                    hitSlop={8}
                  >
                    <Text style={s.copyBtnText}>Copy</Text>
                  </Pressable>
                </View>
              </View>
              <Pressable onPress={()=>openFamily(f)}><Text style={{fontSize:30}}>⚙</Text></Pressable>
            </View>
            {f.members.map(m => (
              <View style={s.member} key={m.id}>
                <MemberAvatar userId={m.user.id} />
                <View style={{flex:1}}>
                  <Text style={s.memberName}>{m.user.username}{profile && m.user.id === profile.id ? ' (You)' : ''}</Text>
                  <Text style={s.mutedSmall}>{m.user.email}</Text>
                  <Text style={s.role}>{m.role}</Text>
                </View>
              </View>
            ))}
            {isMember && !isCreator && (
              <View style={{padding:16}}>
                <Button title="Leave Family" variant="red" onPress={()=>leave(f)} />
              </View>
            )}
          </Card>
        );
      })}
    </>
    <ActionSheet
      visible={sheet}
      title="Create or Join a Family"
      actions={[
        { label: 'Create Family', onPress: () => { setSheet(false); openCreate(); } },
        { label: 'Join Family by Code', onPress: () => { setSheet(false); setJoinOpen(true); } },
      ]}
      onCancel={()=>setSheet(false)}
    />
    <Modal transparent visible={createOpen} animationType="fade">
      <View style={s.overlay}>
        <View style={s.dialog}>
          <Text style={s.dialogTitle}>Create Family</Text>
          <TextInput style={s.input} placeholder="Family name" value={createName} onChangeText={setCreateName} />
          <View style={{height:12}}/>
          <Text style={s.fieldLabel}>Address</Text>
          <AddressInput value={createAddress} onChange={setCreateAddress} placeholder="Please enter your address" enabled={createOpen} />
          <View style={s.dialogActions}>
            <Button title="Cancel" variant="red" onPress={()=>setCreateOpen(false)} />
            <Button title="Confirm" onPress={doCreate} />
          </View>
        </View>
      </View>
    </Modal>
    <InputDialog
      visible={joinOpen}
      title="Join Family by Code"
      placeholder="Enter family code (e.g. F1234567)"
      value={joinCode}
      setValue={setJoinCode}
      onCancel={()=>setJoinOpen(false)}
      onConfirm={doJoin}
    />
  </Screen>;
}
function FamilyDetail({family,onBack,onChange,onDissolve}:{family:Family;onBack:()=>void;onChange:(f:Family)=>void;onDissolve:()=>void}) { const [addr,setAddr]=useState(false); const [val,setVal]=useState(family.address); const save=async()=>{const f=await api.updateFamily(family.id,{address:val.trim()}); onChange(f); setAddr(false)}; return <Screen title="Families" onBack={onBack} onClose={onBack}><Card><Row label="Familie Code" value={family.code}/><Row label="Familie Name" value={family.name} onPress={()=>{}}/><Row label="Address" value={family.address} onPress={()=>{setVal(family.address); setAddr(true);}}/></Card><View style={{height:360}}/><Button title="Dissolve Family" variant="red" onPress={onDissolve}/><Modal transparent visible={addr} animationType="fade"><View style={s.overlay}><View style={s.dialog}><Text style={s.dialogTitle}>Modify address</Text><AddressInput value={val} onChange={setVal} placeholder="Please enter your address" enabled={addr}/><View style={s.dialogActions}><Button title="Cancel" variant="red" onPress={()=>setAddr(false)}/><Button title="Confirm" onPress={save}/></View></View></View></Modal></Screen> }
function Notifications({onBack,settings}:{onBack:()=>void;settings:()=>void}) { const [kind,setKind]=useState<'device'|'system'>('device'); const [read,setRead]=useState(false); return <Screen title="Notification" onBack={onBack} right={<Pressable onPress={settings}><Text style={{fontSize:32}}>⚙</Text></Pressable>}><View style={s.segment}><Pressable onPress={()=>setKind('device')}><Text style={[s.seg,kind==='device'&&s.activeSeg]}>Device notification</Text></Pressable><Pressable onPress={()=>setKind('system')}><Text style={[s.seg,kind==='system'&&s.activeSeg]}>System notification</Text></Pressable></View><View style={s.filters}><Pressable onPress={()=>setRead(false)} style={s.filter}><Text style={{color:colors.red}}>▣ Unread</Text></Pressable><Pressable onPress={()=>setRead(true)} style={s.filter}><Text style={{color:colors.green}}>▣ Read</Text></Pressable></View><EmptyArt/><Text style={s.noNews}>No news at this time.</Text></Screen> }
function NotificationSettings({settings,setSettings,onBack}:{settings:Settings;setSettings:(s:Settings)=>void;onBack:()=>void}) { const patch=async(b:Partial<Settings>)=>setSettings(await api.updateSettings(b)); return <Screen title="Notification" onBack={onBack} onClose={onBack}><Card><View style={s.switchRow}><View><Text style={s.rowLabel}>Device notification</Text><Text style={s.mutedSmall}>Receive device notification</Text></View><Switch value={settings.device_notifications} onValueChange={v=>patch({device_notifications:v})}/></View><View style={s.switchRow}><View><Text style={s.rowLabel}>System notification</Text><Text style={s.mutedSmall}>Receive system notification</Text></View><Switch value={settings.system_notifications} onValueChange={v=>patch({system_notifications:v})}/></View></Card></Screen> }
function Help({onBack,operation}:{onBack:()=>void;operation:()=>void}) { const [open,setOpen]=useState(true); return <Screen title="Help" onBack={onBack} onClose={onBack}><Card><Text style={s.cardTitle}>Advice and feedback</Text><Row label="💬  Contact Us" onPress={()=>setOpen(!open)}/>{open&&<View style={{paddingHorizontal:24,paddingBottom:20}}><Text style={s.contact}>{'Contact number\n+86 0755 2814 0239'}</Text><Text style={s.contact}>{'Email\ninfo@mygardenos.com'}</Text><Text style={s.contact}>{'Official website\nwww.mygardenos.com'}</Text></View>}<Row label="❔  Operation Help" onPress={operation}/></Card></Screen> }
function OperationHelp({onBack,openArticle}:{onBack:()=>void;openArticle:(a:Article)=>void}) { const [arts,setArts]=useState<Article[]>([]); useEffect(()=>{api.articles().then(setArts).catch(()=>{})},[]); return <Screen title="Operation Help" onBack={onBack} onClose={onBack}><Card>{arts.map(a=><Row key={a.slug} label={a.title} onPress={()=>openArticle(a)}/>)}</Card></Screen> }
function ArticleScreen({article,onBack}:{article:Article;onBack:()=>void}) { return <Screen title={article.title} onBack={onBack} onClose={onBack}><View style={s.manual}><Text style={s.manualBadge}>Mowers User Manual</Text><Text style={s.mower}>𐂷</Text><Text style={s.manualBadge}>AN-1600</Text><Text style={s.manualText}>{article.content}</Text></View><View style={s.manual}><Text style={s.manualBadge}>Table of Contents</Text><Text style={s.manualText}>1. Mower Overview ........ 01\n2. Safety Alerts .......... 02-03\n3. Specifications ........ 04\n4. Quick Start Introduction ........ 05-10\n5. Installation and Activation ........ 11-22\n6. Basic Operation of APP ........ 23-33</Text></View></Screen> }
function AboutScreen({about,load,onBack,openText}:{about?:About;load:()=>void;onBack:()=>void;openText:(t:string,b:string)=>void}) { useEffect(()=>{load()},[]); return <Screen title="About" onBack={onBack} onClose={onBack}><View style={s.product}><Text style={{fontSize:120,opacity:.5}}>🤖</Text><Text style={s.emptyTitle}>MYGARDENOS</Text><Text style={{color:'#1B46B0',fontSize:18}}>Version: {about?.version||'V0.1.0-dev'}</Text></View><Card><Row label="Check for Updates" onPress={()=>Alert.alert('Updates',about?.update_status||'Up to date')}/><Row label="Privacy Policy" onPress={()=>openText('Privacy Policy',about?.privacy_policy||'Placeholder')}/><Row label="User Agreement" onPress={()=>openText('User Agreement',about?.user_agreement||'Placeholder')}/></Card></Screen> }
function General({settings,setSettings,onBack}:{settings:Settings;setSettings:(s:Settings)=>void;onBack:()=>void}) { const [sheet,setSheet]=useState(false); const lang=async()=>{setSettings(await api.updateSettings({language:'English'})); setSheet(false)}; return <Screen title="General Settings" onBack={onBack} onClose={onBack}><Card><Row label="Language" value={settings.language} onPress={()=>setSheet(true)}/><Row label="Region" value={settings.region}/><Row label="Clear Cache" onPress={()=>Alert.alert('Clear Cache','Cache cleared')}/></Card><ActionSheet visible={sheet} actions={[{label:'English',onPress:lang}]} onCancel={()=>setSheet(false)}/></Screen> }
function TextPage({title,body,onBack}:{title:string;body:string;onBack:()=>void}) { return <Screen title={title} onBack={onBack} onClose={onBack}><Card><Text style={{fontSize:17,lineHeight:26,padding:20}}>{body}</Text></Card></Screen> }

const s = StyleSheet.create({ iotHeader:{flexDirection:'row',alignItems:'center',gap:14,padding:18,borderBottomWidth:1,borderBottomColor:colors.line}, iotTitle:{fontSize:20,fontWeight:'800',color:colors.text}, iotMuted:{fontSize:14,color:colors.muted,marginTop:4}, iotConfigGrid:{flexDirection:'row',flexWrap:'wrap',gap:10,padding:16}, iotConfigItem:{width:'47%',borderRadius:8,backgroundColor:'#F8FCF8',borderWidth:1,borderColor:colors.line,padding:12}, iotConfigLabel:{fontSize:12,color:colors.muted,fontWeight:'800'}, iotConfigValue:{fontSize:17,color:colors.text,fontWeight:'800',marginTop:5}, iotAtBox:{marginHorizontal:16,marginBottom:16,borderRadius:8,backgroundColor:'#102018',padding:12}, iotAtText:{fontSize:12,lineHeight:18,color:'#D9F7E3',fontFamily:'Courier'}, iotError:{fontSize:14,color:colors.red,marginBottom:14}, iotSectionTitle:{fontSize:19,fontWeight:'800',color:colors.text,marginBottom:12}, iotMessageCard:{borderRadius:8,backgroundColor:'#fff',borderWidth:1,borderColor:colors.line,padding:14,marginBottom:12}, iotMessageTop:{flexDirection:'row',justifyContent:'space-between',gap:12,marginBottom:10}, iotTopic:{fontSize:16,fontWeight:'800',color:colors.green}, iotTime:{fontSize:11,color:colors.muted,flexShrink:1,textAlign:'right'}, iotPayload:{fontSize:12,lineHeight:17,color:'#2D3D34',fontFamily:'Courier'}, root:{flex:1,backgroundColor:'#FAFAFA',paddingTop:48}, homeTop:{height:84,flexDirection:'row',alignItems:'center',justifyContent:'space-between',paddingHorizontal:26,paddingBottom:8}, topRight:{flexDirection:'row',gap:24,alignItems:'center'}, topChip:{backgroundColor:'#E7F1EA',paddingHorizontal:14,paddingVertical:8,borderRadius:18,borderWidth:1,borderColor:colors.line}, topChipText:{fontWeight:'700',color:colors.green,fontSize:14,letterSpacing:.3}, bell:{color:colors.green,fontSize:24}, plusTop:{backgroundColor:colors.green,color:'#fff',width:34,height:34,borderRadius:17,textAlign:'center',fontSize:28,fontWeight:'900',lineHeight:30}, helpCircle:{width:48,height:48,borderRadius:24,backgroundColor:colors.green,alignItems:'center',justifyContent:'center'}, helpText:{fontSize:28,fontWeight:'900',color:'#fff'}, addCircle:{width:48,height:48,borderRadius:24,backgroundColor:'#000',alignItems:'center',justifyContent:'center'}, homeContent:{flex:1}, center:{flex:1,alignItems:'center',justifyContent:'center',paddingHorizontal:30,paddingBottom:40}, emptyTitle:{fontSize:24,fontWeight:'700',color:'#365243',textAlign:'center',marginBottom:10}, muted:{fontSize:16,color:colors.muted,textAlign:'center',lineHeight:24,marginBottom:28}, bigPlus:{backgroundColor:colors.green2,width:74,height:74,borderRadius:37,alignItems:'center',justifyContent:'center',shadowColor:'#184830',shadowOpacity:.18,shadowRadius:8,shadowOffset:{width:0,height:4}}, bottom:{height:112,flexDirection:'row',justifyContent:'space-around',alignItems:'center',backgroundColor:'#F8F8F8'}, tab:{alignItems:'center',gap:4,minWidth:110}, tabIcon:{fontSize:24,color:'#798E7F'}, tabText:{fontSize:18,color:'#8B8B8B',fontWeight:'600'}, deviceCard:{margin:20,padding:22,backgroundColor:'#fff',borderRadius:20,borderWidth:1,borderColor:colors.line,shadowColor:'#153D2A',shadowOpacity:.08,shadowRadius:12,shadowOffset:{width:0,height:6}}, deviceStatus:{fontSize:12,fontWeight:'700',color:colors.green2,letterSpacing:.5,marginBottom:8}, deviceMeta:{fontSize:15,color:colors.muted}, mowerCard:{marginHorizontal:24,marginTop:10,padding:14,backgroundColor:'#fff',borderRadius:8,borderWidth:2,borderColor:'#61ADFF',shadowColor:'#2086F4',shadowOpacity:.3,shadowRadius:14,shadowOffset:{width:0,height:8}}, mowerInfoRow:{flexDirection:'row',gap:14,alignItems:'center'}, mowerArt:{width:116,height:148,alignItems:'center',justifyContent:'center'}, mowerBody:{position:'absolute',width:82,height:122,borderRadius:52,backgroundColor:'#8D8D8D',borderWidth:2,borderColor:'#5D5D5D'}, mowerHandle:{position:'absolute',bottom:12,width:64,height:16,borderRadius:12,backgroundColor:'#fff'}, mowerTop:{position:'absolute',top:0,width:36,height:54,borderRadius:14,backgroundColor:'#FF5A00'}, mowerStop:{position:'absolute',top:72,width:30,height:30,borderRadius:19,backgroundColor:'#FF1B12',color:'#111',fontSize:9,textAlign:'center',lineHeight:30}, mowerWheelLeft:{position:'absolute',left:8,bottom:40,width:14,height:56,borderRadius:8,backgroundColor:'#FF5A00'}, mowerWheelRight:{position:'absolute',right:8,bottom:40,width:14,height:56,borderRadius:8,backgroundColor:'#FF5A00'}, mowerInfo:{flex:1,alignItems:'flex-start'}, schedulePill:{alignSelf:'stretch',minHeight:38,borderRadius:4,backgroundColor:'#63A8F4',alignItems:'center',justifyContent:'center',marginBottom:12}, scheduleText:{fontSize:18,fontWeight:'500',color:'#fff'}, connectionRow:{flexDirection:'row',alignItems:'center',gap:12,marginBottom:6}, bluetoothBadge:{borderWidth:2,borderColor:'#42BF62',borderRadius:4,padding:1}, mowerName:{fontSize:19,color:'#666',fontWeight:'500',marginTop:2}, mowerMeta:{fontSize:18,color:'#666',fontWeight:'500',marginTop:10}, statusPill:{height:42,borderRadius:27,backgroundColor:'#A9CFFA',alignItems:'center',justifyContent:'center',marginVertical:16}, statusPillText:{fontSize:20,color:'#fff',fontWeight:'700'}, actionGrid:{flexDirection:'row',flexWrap:'wrap',gap:12,justifyContent:'space-between'}, deviceAction:{height:74,borderRadius:8,backgroundColor:'#fff',alignItems:'center',justifyContent:'center',shadowColor:'#83BDEF',shadowOpacity:.25,shadowRadius:12,shadowOffset:{width:0,height:7},width:'28%'}, deviceActionWide:{width:'64%',flexDirection:'row',gap:18}, deviceActionText:{fontSize:19,color:'#555',fontWeight:'800'}, deviceActionSmallText:{fontSize:15,color:'#666',fontWeight:'700',marginTop:4}, detailHero:{minHeight:126,borderRadius:8,backgroundColor:'#fff',borderWidth:1,borderColor:colors.line,flexDirection:'row',alignItems:'center',gap:14,padding:16,marginBottom:16}, detailMowerIcon:{width:84,height:84,borderRadius:8,backgroundColor:'#EFF4F0',alignItems:'center',justifyContent:'center'}, detailHeroText:{flex:1,minWidth:0}, detailName:{fontSize:24,fontWeight:'800',color:colors.text,marginBottom:8}, detailMeta:{fontSize:14,color:colors.muted}, detailStatusBadge:{position:'absolute',right:14,top:14,borderRadius:4,backgroundColor:'#A9CFFA',paddingHorizontal:10,paddingVertical:5}, detailStatusText:{fontSize:13,color:'#fff',fontWeight:'800'}, metricGrid:{flexDirection:'row',flexWrap:'wrap',gap:12,marginBottom:18}, metricTile:{width:'48%',minHeight:104,borderRadius:8,backgroundColor:'#fff',borderWidth:1,borderColor:colors.line,alignItems:'center',justifyContent:'center',padding:12}, metricValue:{fontSize:19,fontWeight:'800',color:colors.text,marginTop:6,maxWidth:'100%'}, metricLabel:{fontSize:12,color:colors.muted,fontWeight:'700',marginTop:5}, commandGrid:{flexDirection:'row',flexWrap:'wrap',gap:12,marginBottom:30}, commandButton:{width:'48%',height:86,borderRadius:8,backgroundColor:'#fff',borderWidth:1,borderColor:colors.line,alignItems:'center',justifyContent:'center',shadowColor:'#83BDEF',shadowOpacity:.16,shadowRadius:10,shadowOffset:{width:0,height:5}}, commandText:{fontSize:16,color:'#555',fontWeight:'800',marginTop:5}, addDeviceShell:{alignItems:'center',paddingTop:12,paddingBottom:40}, radar:{width:292,height:292,borderRadius:146,alignSelf:'center',marginTop:20,marginBottom:46,overflow:'hidden',alignItems:'center',justifyContent:'center'}, radarRingOuter:{position:'absolute',width:292,height:292,borderRadius:146,borderWidth:2,borderColor:'#FF542B'}, radarRingMiddle:{position:'absolute',width:194,height:194,borderRadius:97,borderWidth:2,borderColor:'#FF542B'}, radarRingInner:{position:'absolute',width:98,height:98,borderRadius:49,borderWidth:2,borderColor:'#FF542B'}, radarVertical:{position:'absolute',width:2,height:292,backgroundColor:'#FF542B'}, radarHorizontal:{position:'absolute',height:2,width:292,backgroundColor:'#FF542B'}, radarSweepLayer:{position:'absolute',width:292,height:292,left:0,top:0}, radarSweepTrailWide:{position:'absolute',right:0,top:0,width:146,height:146,backgroundColor:'#FFB29C',opacity:.1,transform:[{rotate:'-34deg'}],transformOrigin:'bottom left'}, radarSweepTrailMid:{position:'absolute',right:0,top:0,width:146,height:146,backgroundColor:'#FF9A7B',opacity:.18,transform:[{rotate:'-18deg'}],transformOrigin:'bottom left'}, radarSweep:{position:'absolute',right:0,top:0,width:146,height:146,backgroundColor:'#FF7B55',opacity:.28}, radarSweepFound:{opacity:.35}, radarDot:{position:'absolute',width:12,height:12,borderRadius:6,backgroundColor:'#FF6840'}, radarDotNear:{right:114,top:120}, radarDotFar:{right:24,top:145}, radarDotLow:{right:108,top:197}, addDeviceTitle:{fontSize:24,color:'#666',fontWeight:'800',textAlign:'center',marginBottom:18}, addDeviceCopy:{fontSize:17,lineHeight:25,color:'#A8A8A8',textAlign:'center',paddingHorizontal:8,marginBottom:34}, selectDeviceButton:{height:64,borderRadius:16,backgroundColor:colors.green,alignSelf:'stretch',marginHorizontal:4,alignItems:'center',justifyContent:'center',shadowColor:'#0B3F2B',shadowOpacity:.2,shadowRadius:6,shadowOffset:{width:0,height:4}}, selectDeviceButtonText:{fontSize:22,color:'#fff',fontWeight:'800'}, foundList:{alignSelf:'stretch',paddingHorizontal:2,marginTop:-36}, foundDeviceCard:{minHeight:78,borderRadius:14,borderWidth:1,borderColor:colors.line,backgroundColor:'#fff',flexDirection:'row',alignItems:'center',gap:14,padding:14,marginBottom:12}, foundIcon:{width:48,height:48,borderRadius:24,backgroundColor:'#EAF6EE',alignItems:'center',justifyContent:'center'}, foundName:{fontSize:18,fontWeight:'800',color:colors.text}, foundMeta:{fontSize:13,color:colors.muted,marginTop:4}, rssiText:{fontSize:13,color:colors.green,fontWeight:'700'}, scanAgainButton:{height:52,borderRadius:14,borderWidth:1,borderColor:colors.green,alignItems:'center',justifyContent:'center',marginTop:4}, scanAgainText:{fontSize:16,color:colors.green,fontWeight:'800'}, radarCross:{fontSize:170,color:'#D96545',fontWeight:'100'}, familyHead:{flexDirection:'row',alignItems:'center',justifyContent:'space-between',padding:20}, familyTitle:{fontSize:20,fontWeight:'800',color:colors.green}, familyCode:{fontSize:14,color:colors.muted,fontWeight:'600',letterSpacing:.5}, codeRow:{flexDirection:'row',alignItems:'center',marginTop:4,gap:10}, copyBtn:{paddingHorizontal:10,paddingVertical:4,borderRadius:8,borderWidth:1,borderColor:colors.green,backgroundColor:'#EAF6EE'}, copyBtnText:{color:colors.green,fontSize:12,fontWeight:'700',letterSpacing:.3}, member:{margin:20,marginTop:0,padding:18,backgroundColor:'#EAF1ED',borderRadius:12,flexDirection:'row',gap:16}, memberName:{fontSize:20,color:'#4D5D53'}, mutedSmall:{fontSize:16,color:colors.muted,lineHeight:24}, rowLabel:{fontSize:24,color:'#4B4F56'}, role:{fontSize:18,color:colors.green,fontWeight:'700'}, segment:{flexDirection:'row',justifyContent:'space-around',marginVertical:20}, seg:{fontSize:18,color:'#B6C0B8',fontWeight:'700',paddingBottom:14}, activeSeg:{color:colors.green,borderBottomWidth:3,borderBottomColor:colors.green}, filters:{flexDirection:'row',gap:24}, filter:{backgroundColor:colors.blue,borderRadius:10,padding:14,minWidth:130,alignItems:'center'}, noNews:{textAlign:'center',color:'#555',fontSize:16}, switchRow:{minHeight:96,padding:22,flexDirection:'row',alignItems:'center',justifyContent:'space-between',borderBottomWidth:1,borderBottomColor:colors.line}, cardTitle:{fontSize:23,fontWeight:'800',padding:24}, contact:{fontSize:16,color:colors.muted,lineHeight:24,marginBottom:24}, manual:{backgroundColor:'#fff',marginHorizontal:24,marginBottom:12,alignItems:'center',padding:24,borderWidth:1,borderColor:colors.line,borderRadius:16}, manualBadge:{backgroundColor:'#E44632',color:'#fff',fontWeight:'800',padding:10,margin:10,borderRadius:8}, mower:{fontSize:120,color:'#444'}, manualText:{fontSize:14,lineHeight:24,alignSelf:'stretch'}, product:{alignItems:'center',marginBottom:24}, overlay:{flex:1,backgroundColor:'rgba(0,0,0,.28)',justifyContent:'center',padding:24}, dialog:{backgroundColor:'#fff',borderRadius:18,padding:22,borderWidth:1,borderColor:colors.line}, dialogTitle:{textAlign:'center',fontSize:20,fontWeight:'700',marginBottom:20,color:colors.text}, dialogActions:{flexDirection:'row',marginTop:18}, timeEditor:{borderWidth:1,borderColor:colors.line,borderRadius:14,padding:14,backgroundColor:'#F8FCF8'}, timeLabel:{fontSize:14,color:colors.muted,fontWeight:'800',marginBottom:8}, timeControls:{flexDirection:'row',alignItems:'center',gap:12,paddingLeft:2}, timeStep:{width:52,height:30,borderRadius:10,backgroundColor:'#fff',alignItems:'center',justifyContent:'center',borderWidth:1,borderColor:colors.line}, timeSpacer:{width:72}, timeValueRow:{flexDirection:'row',alignItems:'center',gap:10,marginVertical:6}, timeValue:{width:52,height:48,borderRadius:12,backgroundColor:'#fff',borderWidth:1,borderColor:colors.line,textAlign:'center',lineHeight:48,fontSize:24,fontWeight:'800',color:colors.text}, timeColon:{fontSize:24,fontWeight:'800',color:colors.text}, periodButton:{width:72,height:48,borderRadius:12,backgroundColor:colors.green,alignItems:'center',justifyContent:'center'}, periodText:{fontSize:18,fontWeight:'800',color:'#fff'}, input:{borderWidth:1,borderColor:'#CBD5CE',borderRadius:12,fontSize:17,paddingHorizontal:14,paddingVertical:12,color:colors.text,backgroundColor:'#fff'}, fieldLabel:{fontSize:14,color:colors.muted,fontWeight:'600',marginBottom:6,letterSpacing:.3}, choiceGroup:{gap:10,marginBottom:10}, choiceItem:{borderWidth:1,borderColor:colors.line,borderRadius:12,paddingVertical:14,paddingHorizontal:16,backgroundColor:'#F8FCF8'}, choiceItemActive:{borderColor:colors.green,backgroundColor:'#EAF6EE'}, choiceText:{fontSize:16,fontWeight:'600',color:colors.text,textAlign:'center'}, choiceTextActive:{color:colors.green}, signInPrompt:{padding:22,alignItems:'center'}, signInTitle:{fontSize:21,fontWeight:'800',color:colors.text,textAlign:'center',marginBottom:10}, signInCopy:{fontSize:15,color:colors.muted,textAlign:'center',lineHeight:22,marginBottom:18}, signInButton:{height:48,borderRadius:12,backgroundColor:colors.green,alignSelf:'stretch',alignItems:'center',justifyContent:'center'}, signInButtonText:{fontSize:16,color:'#fff',fontWeight:'800'}, profileHeader:{marginBottom:28}, profileHero:{flexDirection:'row',alignItems:'center',gap:18,paddingHorizontal:2,paddingVertical:10}, profileAvatarBox:{width:112,height:112,borderRadius:12,backgroundColor:'#D8D8D8',overflow:'hidden',alignItems:'center',justifyContent:'center'}, profileAvatarImage:{width:'100%',height:'100%'}, profileAvatarFallback:{width:'100%',height:'100%',alignItems:'center',justifyContent:'center',backgroundColor:'#D7D7D7'}, profileHeroText:{flex:1,minWidth:0}, profileName:{fontSize:28,fontWeight:'800',color:'#202328',marginBottom:12}, profileEmail:{fontSize:18,color:'#A1A1A1',marginBottom:18}, profileQuickRow:{flexDirection:'row',gap:12}, profileQuickButton:{height:42,minWidth:118,borderRadius:10,backgroundColor:'#fff',alignItems:'center',justifyContent:'center',shadowColor:'#7DB8F5',shadowOpacity:.25,shadowRadius:10,shadowOffset:{width:0,height:5}}, profileQuickText:{fontSize:18,fontWeight:'800',color:colors.green}, profileDivider:{height:1,backgroundColor:'#D8ECF2',marginTop:18}, profileMenuRow:{minHeight:82,flexDirection:'row',alignItems:'center',paddingHorizontal:22,gap:18}, profileMenuIconWrap:{width:48,height:48,borderRadius:12,backgroundColor:'#F3FAF9',alignItems:'center',justifyContent:'center'}, profileMenuLabel:{flex:1,fontSize:22,color:'#555',fontWeight:'500'}, suggestionBox:{marginTop:12,borderWidth:1,borderColor:colors.line,borderRadius:12,overflow:'hidden',backgroundColor:'#fff'}, suggestionItem:{paddingVertical:12,paddingHorizontal:14,borderBottomWidth:1,borderBottomColor:colors.line}, suggestionText:{fontSize:15,color:colors.text}, suggestionEmpty:{paddingVertical:12,paddingHorizontal:14,color:colors.muted,fontSize:14} });
