<script setup>
/**
 * 数据看板（管理端）
 * ⚠️ 说明：后端为只读且当前没有「会话/订单聚合」类接口，本页所有数值均为
 *    静态示例数据，UI 已逐块标注「示例数据」。待后端补齐聚合接口后替换数据源即可，
 *    组件与布局无需改动。
 */
import PageHeader from '../components/layout/PageHeader.vue'
import AppCard from '../components/ui/AppCard.vue'
import AppBadge from '../components/ui/AppBadge.vue'
import InlineAlert from '../components/ui/InlineAlert.vue'
import KpiCard from '../components/ui/KpiCard.vue'
import ChartPlaceholder from '../components/ui/ChartPlaceholder.vue'
import StatTable from '../components/ui/StatTable.vue'
import Icon from '../components/ui/Icon.vue'
import { navigate } from '../router/useRoute'

const kpis = [
  { label: '今日会话量', value: 128, unit: '次', delta: '+12.4%', deltaVariant: 'success', hint: '较昨日', icon: 'chat' },
  { label: '平均响应时长', value: '2.6', unit: '秒', delta: '-0.4s', deltaVariant: 'success', hint: '较昨日', icon: 'chart' },
  { label: '一次解决率', value: '86.5', unit: '%', delta: '+1.8%', deltaVariant: 'success', hint: '较昨日', icon: 'checkCircle' },
  { label: '待人工跟进', value: 7, unit: '条', delta: '+2', deltaVariant: 'danger', hint: '较昨日', icon: 'inbox' },
]

const volumeSeries = [
  { label: '周一', value: 96 },
  { label: '周二', value: 112 },
  { label: '周三', value: 88 },
  { label: '周四', value: 134 },
  { label: '周五', value: 152 },
  { label: '周六', value: 118 },
  { label: '周日', value: 128 },
]

const intentSeries = [
  { label: '退款', value: 42 },
  { label: '查订单', value: 68 },
  { label: '商品咨询', value: 55 },
  { label: '退换货', value: 31 },
  { label: '物流', value: 47 },
]

const topicColumns = [
  { key: 'topic', label: '咨询主题' },
  { key: 'count', label: '会话数', align: 'right' },
  { key: 'rate', label: '占比', align: 'right' },
  { key: 'trend', label: '环比', align: 'right' },
]

const topicRows = [
  { id: 't1', topic: '订单状态查询', count: 68, rate: '24.1%', trend: '+3.2%' },
  { id: 't2', topic: '商品咨询', count: 55, rate: '19.5%', trend: '-1.1%' },
  { id: 't3', topic: '物流查询', count: 47, rate: '16.7%', trend: '+0.6%' },
  { id: 't4', topic: '退款申请', count: 42, rate: '14.9%', trend: '+2.4%' },
  { id: 't5', topic: '退换货政策', count: 31, rate: '11.0%', trend: '-0.8%' },
]
</script>

<template>
  <div class="admin-view">
    <div class="admin-view__inner">
      <PageHeader
        title="数据看板"
        subtitle="客服会话与服务质量概览。"
        :breadcrumb="[{ label: '管理端' }, { label: '数据看板' }]"
        @navigate="navigate"
      >
        <template #actions>
          <AppBadge variant="warning">本页为示例数据</AppBadge>
        </template>
      </PageHeader>

      <InlineAlert
        class="notice"
        variant="info"
        message="后端当前未提供看板聚合接口（且本方案不改动后端），本页数值为静态示例数据，仅用于演示布局与视觉规范。"
      />

      <div class="kpi-grid">
        <AppCard v-for="kpi in kpis" :key="kpi.label" class="kpi-grid__item">
          <KpiCard
            :label="kpi.label"
            :value="kpi.value"
            :unit="kpi.unit"
            :delta="kpi.delta"
            :delta-variant="kpi.deltaVariant"
            :hint="kpi.hint"
          >
            <template #icon><Icon :name="kpi.icon" :size="16" /></template>
          </KpiCard>
        </AppCard>
      </div>

      <div class="chart-grid">
        <AppCard>
          <ChartPlaceholder
            title="近 7 日会话量"
            subtitle="单位：次"
            :series="volumeSeries"
            :height="182"
          />
        </AppCard>
        <AppCard>
          <ChartPlaceholder
            title="咨询意图分布"
            subtitle="单位：次"
            :series="intentSeries"
            :height="182"
          />
        </AppCard>
      </div>

      <AppCard class="table-card">
        <StatTable
          title="咨询主题排行"
          sample
          :columns="topicColumns"
          :rows="topicRows"
          row-key="id"
        />
      </AppCard>
    </div>
  </div>
</template>

<style scoped>
.admin-view {
  padding: var(--space-6);
}
.admin-view__inner {
  width: min(var(--content-max), 100%);
  margin: 0 auto;
}

.notice {
  margin-bottom: var(--space-4);
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: var(--space-4);
}

.kpi-grid__item {
  min-height: 128px;
}

.chart-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: var(--space-4);
  margin-top: var(--space-4);
}

.table-card {
  margin-top: var(--space-4);
}

@media (max-width: 1179px) {
  .kpi-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .chart-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 767px) {
  .admin-view {
    padding: var(--space-4);
  }
  .kpi-grid {
    grid-template-columns: 1fr;
  }
}
</style>
