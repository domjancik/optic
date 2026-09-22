export function shortcutLayer(event,layers){
  if(!event.shiftKey||event.ctrlKey||event.altKey||event.metaKey)return null;
  const match=/^(?:Digit|Numpad)(\d)$/.exec(event.code);
  if(!match)return null;
  const number=Number(match[1]);
  return number===0?'screen':number===1?'source':layers[number-2]?.id??null;
}
