<script setup lang="ts">
const appName = "Legions";
</script>

<template>
  <main class="layout">
    <h1>{{ appName }}</h1>
    <p>Vue + PixiJS frontend scaffold is ready.</p>
  </main>
</template>

<style scoped>
.layout {
  min-height: 100dvh;
  display: grid;
  place-items: center;
  text-align: center;
  padding: 2rem;
  font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
}
</style>
