import React from 'react';
import { Image, Modal, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native';
import { colors } from '../theme/colors';

export function Screen({ title, children, onBack, onClose, right }: {title?:string; children:React.ReactNode; onBack?:()=>void; onClose?:()=>void; right?:React.ReactNode}) {
  return <View style={s.screen}><View style={s.nav}><Pressable onPress={onBack}><Text style={s.navIcon}>‹</Text></Pressable><Text style={s.title}>{title}</Text><View style={s.navRight}>{right}{onClose && <Pressable onPress={onClose}><Text style={s.close}>×</Text></Pressable>}</View></View><ScrollView contentContainerStyle={s.body}>{children}</ScrollView></View>;
}
export function Card({ children }: {children:React.ReactNode}) { return <View style={s.card}>{children}</View>; }
export function Row({ label, value, onPress, danger, avatarUri, hideChev }: {label:string; value?:string; onPress?:()=>void; danger?:boolean; avatarUri?:string; hideChev?:boolean}) { return <Pressable onPress={onPress} style={s.row}><Text style={[s.rowLabel, danger && {color:colors.darkRed}]}>{label}</Text><View style={s.rowValueWrap}>{avatarUri ? <Image source={{uri:avatarUri}} style={s.rowAvatar}/> : value ? <Text style={s.rowValue}>{value}</Text> : null}{onPress && !hideChev && <Text style={s.chev}>›</Text>}</View></Pressable>; }
export function Button({ title, onPress, variant='green' }: {title:string; onPress:()=>void; variant?:'green'|'red'|'light'}) { const bg = variant==='red'?colors.red:variant==='light'?colors.card:colors.green; return <Pressable onPress={onPress} style={[s.button,{backgroundColor:bg}, variant==='light' && s.buttonLight]}><Text style={[s.buttonText, variant==='light' && {color:colors.green}]}>{title}</Text></Pressable>; }
export function EmptyArt() { return <View style={s.emptyArt}><Text style={s.sparkle}>✦  ◦       ✳</Text><Text style={s.bubble}>?</Text><Text style={s.shadow}>▰</Text></View>; }
export function InputDialog({ visible, title, placeholder, value, setValue, onCancel, onConfirm }: {visible:boolean; title:string; placeholder:string; value:string; setValue:(v:string)=>void; onCancel:()=>void; onConfirm:()=>void}) { return <Modal transparent visible={visible} animationType="fade"><View style={s.overlay}><View style={s.dialog}><Text style={s.dialogTitle}>{title}</Text><TextInput style={s.input} placeholder={placeholder} value={value} onChangeText={setValue}/><View style={s.dialogActions}><Button title="Cancel" variant="red" onPress={onCancel}/><Button title="Confirm" onPress={onConfirm}/></View></View></View></Modal>; }
export function ActionSheet({ visible, title, actions, onCancel }: {visible:boolean; title?:string; actions:{label:string; onPress:()=>void}[]; onCancel:()=>void}) { return <Modal transparent visible={visible} animationType="slide"><View style={s.sheetOverlay}><View style={s.sheet}>{title && <Text style={s.sheetTitle}>{title}</Text>}{actions.map(a=><Pressable key={a.label} onPress={a.onPress} style={s.sheetItem}><Text style={s.sheetText}>{a.label}</Text></Pressable>)}</View><Pressable onPress={onCancel} style={s.cancelSheet}><Text style={s.sheetText}>Cancel</Text></Pressable></View></Modal>; }

const s = StyleSheet.create({
  screen:{flex:1,backgroundColor:colors.bg,paddingTop:48},
  nav:{height:64,flexDirection:'row',alignItems:'center',justifyContent:'space-between',paddingHorizontal:20,borderBottomWidth:1,borderBottomColor:colors.line,backgroundColor:'#F7FBF6'},
  navIcon:{fontSize:36,color:colors.text},
  close:{fontSize:34,color:colors.text,marginLeft:14},
  navRight:{minWidth:60,flexDirection:'row',justifyContent:'flex-end',alignItems:'center'},
  title:{fontWeight:'800',fontSize:22,color:colors.text,letterSpacing:.2},
  body:{padding:20,paddingBottom:42},
  card:{backgroundColor:colors.card,borderRadius:20,borderWidth:1,borderColor:colors.line,marginBottom:18,overflow:'hidden',shadowColor:'#0D3A26',shadowOpacity:.08,shadowRadius:12,shadowOffset:{width:0,height:6}},
  row:{minHeight:68,paddingHorizontal:18,flexDirection:'row',alignItems:'center',justifyContent:'space-between',borderBottomWidth:1,borderBottomColor:colors.line},
  rowLabel:{fontSize:17,color:'#3E5044',fontWeight:'500'},
  rowValueWrap:{flexDirection:'row',alignItems:'center'},
  rowValue:{fontSize:16,color:colors.muted,marginRight:10},
  rowAvatar:{width:40,height:40,borderRadius:20,marginRight:10,backgroundColor:'#E5EFE9'},
  chev:{fontSize:36,color:'#314436'},
  button:{borderRadius:16,minHeight:54,alignItems:'center',justifyContent:'center',paddingHorizontal:18,flex:1,marginHorizontal:6},
  buttonLight:{borderWidth:1,borderColor:colors.line},
  buttonText:{color:'#fff',fontWeight:'700',fontSize:17},
  emptyArt:{alignItems:'center',marginVertical:34},
  sparkle:{color:'#5DB47D',fontSize:24},
  bubble:{fontSize:70,color:'#86C49E',borderColor:'#B9DCC5',borderWidth:4,borderRadius:56,width:112,height:112,textAlign:'center',backgroundColor:'#EDF7F0'},
  shadow:{color:'#9FCCAF',fontSize:64,marginTop:-40,opacity:.7},
  overlay:{flex:1,backgroundColor:'rgba(0,0,0,.28)',justifyContent:'center',padding:24},
  dialog:{backgroundColor:'#fff',borderRadius:18,padding:22,borderWidth:1,borderColor:colors.line},
  dialogTitle:{textAlign:'center',fontSize:20,fontWeight:'700',marginBottom:28,color:colors.text},
  input:{borderBottomWidth:1,borderBottomColor:'#B6C4BA',fontSize:17,marginBottom:28,padding:8,color:colors.text},
  dialogActions:{flexDirection:'row'},
  sheetOverlay:{flex:1,backgroundColor:'rgba(0,0,0,.25)',justifyContent:'flex-end',padding:10},
  sheet:{backgroundColor:'#fff',borderRadius:18,overflow:'hidden'},
  sheetTitle:{textAlign:'center',fontSize:15,color:colors.muted,padding:14,borderBottomWidth:1,borderBottomColor:colors.line},
  sheetItem:{padding:20,alignItems:'center',borderBottomWidth:1,borderBottomColor:colors.line},
  sheetText:{fontSize:20,color:colors.green,fontWeight:'600'},
  cancelSheet:{backgroundColor:'#fff',borderRadius:18,alignItems:'center',padding:18,marginTop:10,marginBottom:16},
});
