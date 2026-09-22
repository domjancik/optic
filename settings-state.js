/** Older select controls persisted numeric values as strings. Preserve their values. */
export function normalizeSettings(saved, defaults){
  const settings={...defaults,...saved};
  for(const [key,example] of Object.entries(defaults)){
    if(typeof example!=='number')continue;
    const value=settings[key];
    if((typeof value!=='number'&&typeof value!=='string')||String(value).trim()===''||!Number.isFinite(Number(value)))throw Error(`${key} must be a finite number`);
    settings[key]=Number(value);
  }
  return settings;
}
