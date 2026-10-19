"""Plot the estimates from one repeated-sampling condition; one count per trial."""
import argparse,csv,json
from pathlib import Path

def draw(folder):
    summary=json.loads((folder/'summary.json').read_text())
    with (folder/'trials.csv').open(encoding='utf-8',newline='') as f:values=[float(r['estimate']) for r in csv.DictReader(f) if r['estimate']!='']
    if not values:raise ValueError("全部轮次的估计都未定义，无法画估计分布；请先检查无回答或缺组")
    counts=[0]*20
    for x in values:counts[min(int(x*20),19)]+=1
    top=max(counts) or 1
    s=['<svg xmlns="http://www.w3.org/2000/svg" width="900" height="430" viewBox="0 0 900 430">','<rect width="900" height="430" fill="white"/>','<g font-family="sans-serif" font-size="16" fill="#183346">','<text x="65" y="30">抽样分布的模拟：每一次调查只贡献一个估计值</text>']
    for i,count in enumerate(counts):
        h=270*count/top;s.append(f'<rect x="{70+i*39}" y="{350-h:.3f}" width="38" height="{h:.3f}" fill="#3986b1"/>')
    for i in range(6):s.append(f'<text x="{60+i*156}" y="380">{i*20}%</text>')
    s+=['<path d="M70 65 V350 H850" stroke="#183346" fill="none"/>',f'<text x="5" y="85">{top}次</text>','<text x="22" y="350">0</text>']
    x=70+780*summary['truth'];s+=[f'<path d="M{x:.3f} 60 V350" stroke="#bf4c25" stroke-width="2" stroke-dasharray="6 4"/>',f'<text x="{x+8:.3f}" y="58" fill="#bf4c25">总体真值 {100*summary["truth"]:.1f}%</text>','<text x="345" y="414">每次调查得到的需求比例</text>','</g></svg>']
    (folder/'distribution.svg').write_text('\n'.join(s)+'\n',encoding='utf-8');print(folder/'distribution.svg')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);draw(p.parse_args().run)
