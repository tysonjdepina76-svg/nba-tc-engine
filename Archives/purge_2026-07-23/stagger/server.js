const { spawn } = require('child_process');

const SERVICES = [
  { name: 'api', cmd: 'uvicorn', args: ['api.main:app', '--host', '0.0.0.0', '--port', '8000', '--reload'], delay: 0 },
  { name: 'dashboard', cmd: 'streamlit', args: ['run', 'tc_dashboard.py', '--server.port', '8510', '--server.address', '0.0.0.0'], delay: 5 },
  { name: 'redis', cmd: 'redis-server', args: ['--port', '6379', '--bind', '127.0.0.1'], delay: 2 },
  { name: 'telegram', cmd: 'python3', args: ['telegram_bot.py'], delay: 10 },
];

const children = [];

function startService(service) {
  const child = spawn(service.cmd, service.args, {
    cwd: '/home/workspace/Projects',
    stdio: 'inherit',
    env: { ...process.env },
  });

  child.on('error', (err) => {
    console.error(`[${service.name}] Failed to start: ${err.message}`);
  });

  child.on('exit', (code, signal) => {
    console.log(`[${service.name}] Exited with code ${code}, signal ${signal}. Restarting in 3s...`);
    setTimeout(() => startService(service), 3000);
  });

  children.push(child);
  return child;
}

function staggeredStart() {
  let cumulativeDelay = 0;
  for (const service of SERVICES) {
    cumulativeDelay += service.delay;
    setTimeout(() => {
      console.log(`[stagger] Starting ${service.name} (delay=${service.delay}s, total=${cumulativeDelay}s)`);
      startService(service);
    }, cumulativeDelay * 1000);
  }
}

process.on('SIGTERM', () => {
  console.log('[stagger] Shutting down...');
  for (const child of children) {
    child.kill('SIGTERM');
  }
  setTimeout(() => process.exit(0), 5000);
});

process.on('SIGINT', () => {
  console.log('[stagger] Interrupted, shutting down...');
  for (const child of children) {
    child.kill('SIGINT');
  }
  setTimeout(() => process.exit(0), 3000);
});

console.log('[stagger] TC Sports staggered server starting...');
staggeredStart();
