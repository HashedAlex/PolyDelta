// 球队名称中英文映射

// NBA 球队名称
export const NBA_TEAM_NAMES: Record<string, string> = {
  // 东部联盟 - 大西洋分区
  'Boston Celtics': '波士顿凯尔特人',
  'Brooklyn Nets': '布鲁克林篮网',
  'New York Knicks': '纽约尼克斯',
  'Philadelphia 76ers': '费城76人',
  'Toronto Raptors': '多伦多猛龙',

  // 东部联盟 - 中部分区
  'Chicago Bulls': '芝加哥公牛',
  'Cleveland Cavaliers': '克利夫兰骑士',
  'Detroit Pistons': '底特律活塞',
  'Indiana Pacers': '印第安纳步行者',
  'Milwaukee Bucks': '密尔沃基雄鹿',

  // 东部联盟 - 东南分区
  'Atlanta Hawks': '亚特兰大老鹰',
  'Charlotte Hornets': '夏洛特黄蜂',
  'Miami Heat': '迈阿密热火',
  'Orlando Magic': '奥兰多魔术',
  'Washington Wizards': '华盛顿奇才',

  // 西部联盟 - 西北分区
  'Denver Nuggets': '丹佛掘金',
  'Minnesota Timberwolves': '明尼苏达森林狼',
  'Oklahoma City Thunder': '俄克拉荷马城雷霆',
  'Portland Trail Blazers': '波特兰开拓者',
  'Utah Jazz': '犹他爵士',

  // 西部联盟 - 太平洋分区
  'Golden State Warriors': '金州勇士',
  'Los Angeles Clippers': '洛杉矶快船',
  'Los Angeles Lakers': '洛杉矶湖人',
  'Phoenix Suns': '菲尼克斯太阳',
  'Sacramento Kings': '萨克拉门托国王',

  // 西部联盟 - 西南分区
  'Dallas Mavericks': '达拉斯独行侠',
  'Houston Rockets': '休斯顿火箭',
  'Memphis Grizzlies': '孟菲斯灰熊',
  'New Orleans Pelicans': '新奥尔良鹈鹕',
  'San Antonio Spurs': '圣安东尼奥马刺',
}

// FIFA 世界杯国家队名称
export const FIFA_TEAM_NAMES: Record<string, string> = {
  // 欧洲
  'France': '法国',
  'Germany': '德国',
  'Spain': '西班牙',
  'England': '英格兰',
  'Italy': '意大利',
  'Portugal': '葡萄牙',
  'Netherlands': '荷兰',
  'Belgium': '比利时',
  'Croatia': '克罗地亚',
  'Denmark': '丹麦',
  'Switzerland': '瑞士',
  'Poland': '波兰',
  'Serbia': '塞尔维亚',
  'Ukraine': '乌克兰',
  'Austria': '奥地利',
  'Czech Republic': '捷克',
  'Wales': '威尔士',
  'Scotland': '苏格兰',
  'Sweden': '瑞典',
  'Norway': '挪威',
  'Hungary': '匈牙利',
  'Turkey': '土耳其',
  'Russia': '俄罗斯',
  'Greece': '希腊',
  'Romania': '罗马尼亚',
  'Slovakia': '斯洛伐克',
  'Slovenia': '斯洛文尼亚',
  'Republic of Ireland': '爱尔兰',
  'Ireland': '爱尔兰',
  'Northern Ireland': '北爱尔兰',
  'Iceland': '冰岛',
  'Finland': '芬兰',
  'Bosnia and Herzegovina': '波黑',
  'Albania': '阿尔巴尼亚',
  'North Macedonia': '北马其顿',
  'Montenegro': '黑山',
  'Georgia': '格鲁吉亚',

  // 南美洲
  'Brazil': '巴西',
  'Argentina': '阿根廷',
  'Uruguay': '乌拉圭',
  'Colombia': '哥伦比亚',
  'Chile': '智利',
  'Peru': '秘鲁',
  'Ecuador': '厄瓜多尔',
  'Paraguay': '巴拉圭',
  'Venezuela': '委内瑞拉',
  'Bolivia': '玻利维亚',

  // 北美洲及中美洲
  'USA': '美国',
  'United States': '美国',
  'Mexico': '墨西哥',
  'Canada': '加拿大',
  'Costa Rica': '哥斯达黎加',
  'Panama': '巴拿马',
  'Jamaica': '牙买加',
  'Honduras': '洪都拉斯',
  'El Salvador': '萨尔瓦多',
  'Guatemala': '危地马拉',

  // 非洲
  'Morocco': '摩洛哥',
  'Senegal': '塞内加尔',
  'Nigeria': '尼日利亚',
  'Cameroon': '喀麦隆',
  'Ghana': '加纳',
  'Egypt': '埃及',
  'Algeria': '阿尔及利亚',
  'Tunisia': '突尼斯',
  'Ivory Coast': '科特迪瓦',
  "Côte d'Ivoire": '科特迪瓦',
  'South Africa': '南非',
  'Mali': '马里',
  'DR Congo': '刚果民主共和国',

  // 亚洲
  'Japan': '日本',
  'South Korea': '韩国',
  'Korea Republic': '韩国',
  'Australia': '澳大利亚',
  'Saudi Arabia': '沙特阿拉伯',
  'Iran': '伊朗',
  'Qatar': '卡塔尔',
  'Iraq': '伊拉克',
  'United Arab Emirates': '阿联酋',
  'UAE': '阿联酋',
  'China': '中国',
  'China PR': '中国',
  'Vietnam': '越南',
  'Thailand': '泰国',
  'Indonesia': '印度尼西亚',
  'Uzbekistan': '乌兹别克斯坦',
  'Jordan': '约旦',
  'Oman': '阿曼',
  'Bahrain': '巴林',
  'Palestine': '巴勒斯坦',
  'Syria': '叙利亚',
  'Lebanon': '黎巴嫩',
  'India': '印度',

  // 大洋洲
  'New Zealand': '新西兰',
}

// 获取球队的中文名称
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function getTeamNameChinese(englishName: string, sportType?: string): string {
  // 先尝试完全匹配
  if (NBA_TEAM_NAMES[englishName]) {
    return NBA_TEAM_NAMES[englishName]
  }
  if (FIFA_TEAM_NAMES[englishName]) {
    return FIFA_TEAM_NAMES[englishName]
  }

  // 尝试部分匹配 (处理 "Boston Celtics" vs "Celtics" 这种情况)
  for (const [en, zh] of Object.entries(NBA_TEAM_NAMES)) {
    if (englishName.includes(en) || en.includes(englishName)) {
      return zh
    }
  }
  for (const [en, zh] of Object.entries(FIFA_TEAM_NAMES)) {
    if (englishName.includes(en) || en.includes(englishName)) {
      return zh
    }
  }

  // 没找到则返回原名
  return englishName
}

// 获取球队名称 (根据语言)
export function getLocalizedTeamName(englishName: string, language: string, sportType?: string): string {
  if (language === 'zh') {
    return getTeamNameChinese(englishName, sportType)
  }
  return englishName
}
