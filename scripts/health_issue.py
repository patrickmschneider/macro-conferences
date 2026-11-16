"""Keep one GitHub issue in step with the alerts in data/run-status.json.

Opens the issue when alerts appear, comments only when a new alert arrives (so a persistent
problem does not send a daily email), and closes it when the alerts clear. GitHub notifies
the repository owner of new issues and comments, so a broken source, a missed known call
or stalled discovery reaches a person without anyone watching the site.
Runs in GitHub Actions with GH_TOKEN set; elsewhere it prints what it would do."""
import json,os,re,subprocess,sys
from pathlib import Path
TITLE='Conference tracker needs attention'
ROOT=Path(__file__).resolve().parents[1]

def gh(*args):return subprocess.run(['gh',*args],check=True,capture_output=True,text=True).stdout

def body(status):
 alerts=status.get('alerts',[])
 lines=['The daily update raised these alerts:','',*[f"- {a['text']}" for a in alerts],'',
  f"Latest run: {status.get('last_run','unknown')}. Fix or disable the source in `sources.yaml`, or add the missed call's series to it. This issue closes itself when the alerts clear.",
  f"<!-- alert-keys: {json.dumps(sorted(a['key'] for a in alerts))} -->"]
 return '\n'.join(lines)

def main():
 status=json.loads((ROOT/'data/run-status.json').read_text());alerts=status.get('alerts',[])
 if not os.environ.get('GH_TOKEN'):
  print(f'{len(alerts)} alerts (GH_TOKEN unset; no issue update)');[print(' -',a['text']) for a in alerts];return
 issues=json.loads(gh('issue','list','--state','open','--search',f'"{TITLE}" in:title','--json','number,title,body'))
 issue=next((i for i in issues if i['title']==TITLE),None)
 if alerts and not issue:
  gh('issue','create','--title',TITLE,'--body',body(status));print('Opened health issue')
 elif alerts:
  m=re.search(r'<!-- alert-keys: (.*?) -->',issue['body'] or '');old=set(json.loads(m[1])) if m else set()
  new=[a for a in alerts if a['key'] not in old]
  gh('issue','edit',str(issue['number']),'--body',body(status))
  if new:gh('issue','comment',str(issue['number']),'--body','New alerts:\n'+'\n'.join(f"- {a['text']}" for a in new))
  print(f'Updated health issue #{issue["number"]} ({len(new)} new alerts)')
 elif issue:
  gh('issue','close',str(issue['number']),'--comment','All alerts cleared in the latest run.');print('Closed health issue')

if __name__=='__main__':
 try:main()
 except subprocess.CalledProcessError as ex:
  # Reporting must never fail the data update itself.
  print('Health issue update failed:',ex.stderr,file=sys.stderr)
