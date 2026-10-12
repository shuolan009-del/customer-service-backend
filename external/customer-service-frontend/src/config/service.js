import xiaoerAvatar from '../assets/xiaoer.png'
import userProfileAvatar from '../assets/userProfileAvatar.svg'

/**
 * 客服 / 用户身份配置（工作台与会话记录共用，避免多处硬编码）。
 * 数字人形象名走《魔珐星云》的「小宝」，与后端无关。
 */

export const customerService = {
  name: '小宝',
  title: '金牌客服',
  status: '在线',
  avatar: xiaoerAvatar,
}

export const userProfile = {
  name: '你',
  label: '用户',
  avatar: userProfileAvatar,
}

/**
 * 默认用户身份。设置页可改（cs-prefs.defaultSenderId），
 * 工作台 / 会话记录 / 设置页共用同一默认值，避免多处硬编码。
 */
export const DEFAULT_SENDER_ID = 'u1001'

/** 欢迎态快捷问题 */
export const QUICK_QUESTIONS = ['我要退款', '查订单状态', '商品推荐', '退换货政策']
