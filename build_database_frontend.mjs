// Build an isolated database-connected version of the existing app without
// editing/copying its source checkout. Only two modules change in memory.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import path from 'node:path';
import {pathToFileURL, fileURLToPath} from 'node:url';
const root = path.dirname(fileURLToPath(import.meta.url));
const source = path.resolve(process.argv[2]);
const output = path.resolve(root, 'web', 'roomies');
// Vite may clear output. Verify the absolute target before permitting it.
if (!output.startsWith(root + path.sep) || output !== path.join(root, 'web', 'roomies') || output === source) throw new Error('Unsafe build output path.');
const importFrom = relative => import(pathToFileURL(path.join(source, 'node_modules', relative)).href);
const {build} = await importFrom('vite/dist/node/index.js');
const typescriptModule = await importFrom('typescript/lib/typescript.js');
const ts = typescriptModule.default || typescriptModule;
const hookPath = path.join(source, 'app', 'hooks', 'useHouseholdLedger.ts');
const dashboardPath = path.join(source, 'app', 'components', 'dashboard', 'HouseholdDashboard.tsx');
const hook = await readFile(path.join(root, 'frontend', 'useHouseholdLedger.ts'), 'utf8');
const original = await readFile(dashboardPath, 'utf8');
const call = "useHouseholdLedger(assignedHousehold?.name || localData.household || 'personal ' + user.email, expenseRoster)";
if (!original.includes(call)) throw new Error('Roomies changed its ledger interface. Review the adapter before rebuilding.');
const dashboard = original.replace(call, call.slice(0, -1) + ', {email: user.email, householdId: user.demoHouseholdId})');
const normalize = value => path.resolve(value.split('?')[0]).replaceAll('\\', '/');
const replacements = new Map([[normalize(hookPath), hook], [normalize(dashboardPath), dashboard]]);
const configPath = path.join(source, 'tsconfig.json');
const config = ts.readConfigFile(configPath, ts.sys.readFile);
const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, source);
const host = ts.createCompilerHost(parsed.options);
const read = host.readFile.bind(host);
host.readFile = name => replacements.get(normalize(name)) ?? read(name);
const program = ts.createProgram(parsed.fileNames, {...parsed.options, noEmit: true}, host);
const diagnostics = ts.getPreEmitDiagnostics(program);
if (diagnostics.length) { process.stderr.write(ts.formatDiagnosticsWithColorAndContext(diagnostics, {getCurrentDirectory: () => source, getNewLine: () => '\n', getCanonicalFileName: name => name})); process.exit(1); }
await mkdir(output, {recursive: true});
await build({root: source, configFile: path.join(source, 'vite.config.ts'),
  plugins: [{name: 'roomies-csc4402-expenses', enforce: 'pre', transform(code, id) { return replacements.get(normalize(id)) ?? null; }}],
  build: {outDir: output, emptyOutDir: true}});
await writeFile(path.join(output, 'roomies-4402-build.json'), JSON.stringify({expenseLedger: true, source: 'Jenahh/Roomies', adapter: 'SQL expense ledger'}, null, 2));
console.log('Database-connected Roomies build: ' + output);
console.log('The original Roomies source and its dist folder were not edited.');
