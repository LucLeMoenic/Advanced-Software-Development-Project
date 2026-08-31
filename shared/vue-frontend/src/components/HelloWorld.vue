<template>
  <section>
    <p>{{ msg }}</p>
    <button @click="count++">Clicked {{ count }} times</button>
  </section>
</template>

<script setup>
import { ref } from "vue";
const props = defineProps({ msg: String });
const count = ref(0);
</script>

<style scoped>
section {
  margin-top: 1rem;
}
button {
  padding: 0.5rem 1rem;
}
</style>
