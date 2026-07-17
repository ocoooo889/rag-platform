<template>
  <router-view />
</template>

<script setup>
import { onMounted } from 'vue'
import { useBrandingStore } from '@/stores/branding'

onMounted(async () => {
  try {
    await useBrandingStore().fetchBranding()
  } catch (error) {
    console.error('Failed to initialize branding:', error)
  }
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
}
</style>