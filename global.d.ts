declare const __WSURL__: string

declare const __WORKERPATH__: ".scanDirectoryWoker.ts" | "./scanDirectoryWorker.js"

declare module "*.png" {
  const src: string;
  export default src;
}